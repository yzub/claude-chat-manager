using System.Text.Json;
using System.Text.Json.Nodes;

namespace ClaudeChatManager;

public static class ChatScanner
{
	private static readonly string ClaudeDir = Path.Combine(
		Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".claude");

	private static readonly string ProjectsDir = Path.Combine(ClaudeDir, "projects");

	public static List<ProjectInfo> GetProjects()
	{
		if (!Directory.Exists(ProjectsDir))
			return [];

		return Directory.GetDirectories(ProjectsDir)
			.Select(dir =>
			{
				var folderName = Path.GetFileName(dir);
				// folder name is the path with dashes instead of slashes: -Users-jazz-project
				var projectPath = "/" + folderName.TrimStart('-').Replace('-', '/');
				return new ProjectInfo(projectPath, dir);
			})
			.OrderBy(p => p.Name)
			.ToList();
	}

	public static List<ConversationInfo> GetConversations(string projectDir)
	{
		var byId = new Dictionary<string, ConversationInfo>(StringComparer.Ordinal);

		foreach (var file in Directory.GetFiles(projectDir, "*.jsonl"))
		{
			try
			{
				var conv = ParseConversation(file);

				// Claude's rename sidecar is authoritative
				var customTitle = ReadCustomTitle(file);
				if (!string.IsNullOrWhiteSpace(customTitle))
					conv = conv with { Title = customTitle };

				byId[conv.SessionId] = conv;
			}
			catch
			{
				// skip corrupt files
			}
		}

		// collapse each continuation chain into one row, named by its live head
		var chains = new Dictionary<string, List<ConversationInfo>>(StringComparer.Ordinal);
		foreach (var conv in byId.Values)
		{
			var headId = ResolveHeadId(conv, byId);
			if (!chains.TryGetValue(headId, out var chain))
				chains[headId] = chain = [];

			chain.Add(conv);
		}

		var conversations = new List<ConversationInfo>();
		foreach (var chain in chains.Values)
		{
			var ordered = OrderChain(chain, byId);
			var root = ordered[0];
			var head = ordered[^1];
			var first = ordered.FirstOrDefault(c => !c.IsEmpty);

			conversations.Add(new ConversationInfo(
				root.FilePath,
				head.Title,
				head.Date,
				first?.FirstMessage ?? "{empty}")
			{
				ContinuedInSessionId = root.ContinuedInSessionId,
				SessionId = head.SessionId,
				IsEmpty = first == null,
			});
		}

		return conversations.OrderByDescending(c => c.Date).ToList();
	}

	private static string ResolveHeadId(ConversationInfo conv, Dictionary<string, ConversationInfo> byId)
	{
		var current = conv;
		var seen = new HashSet<string>(StringComparer.Ordinal);

		while (seen.Add(current.SessionId))
		{
			if (string.IsNullOrEmpty(current.ContinuedInSessionId)
				|| !byId.TryGetValue(current.ContinuedInSessionId, out var next))
				return current.SessionId;

			current = next;
		}

		return current.SessionId;
	}

	private static List<ConversationInfo> OrderChain(List<ConversationInfo> chain, Dictionary<string, ConversationInfo> byId)
	{
		var ids = chain.Select(c => c.SessionId).ToHashSet(StringComparer.Ordinal);
		var root = chain.FirstOrDefault(c =>
			!chain.Any(other => other.ContinuedInSessionId == c.SessionId)) ?? chain[0];

		var ordered = new List<ConversationInfo>();
		var seen = new HashSet<string>(StringComparer.Ordinal);
		var current = root;

		while (seen.Add(current.SessionId))
		{
			ordered.Add(current);

			if (string.IsNullOrEmpty(current.ContinuedInSessionId)
				|| !byId.TryGetValue(current.ContinuedInSessionId, out var next)
				|| !ids.Contains(next.SessionId))
				break;

			current = next;
		}

		return ordered;
	}

	private static ConversationInfo ParseConversation(string filePath)
	{
		var sessionId = Path.GetFileNameWithoutExtension(filePath);
		string? firstUserMessage = null;
		string? slugTitle = null;
		string? aiTitle = null;
		string? customTitle = null;
		string? continuedIn = null;
		DateTime? timestamp = null;

		foreach (var line in File.ReadLines(filePath))
		{
			if (string.IsNullOrWhiteSpace(line)) continue;

			JsonlMessage? msg;
			try
			{
				msg = JsonSerializer.Deserialize(line, AppJsonContext.Default.JsonlMessage);
			}
			catch
			{
				continue;
			}

			if (msg == null) continue;

			// grab the timestamp from the first message
			timestamp ??= ParseTimestamp(msg.Timestamp) ?? File.GetCreationTime(filePath);

			// grab slug from first message that has one
			if (slugTitle == null && !string.IsNullOrEmpty(msg.Slug))
				slugTitle = FormatSlug(msg.Slug);

			// Claude can write these events more than once; keep the latest
			if (!string.IsNullOrEmpty(msg.AiTitle))
				aiTitle = msg.AiTitle;

			if (!string.IsNullOrEmpty(msg.CustomTitle))
				customTitle = msg.CustomTitle;

			if (!string.IsNullOrEmpty(msg.ContinuedInSessionId))
				continuedIn = msg.ContinuedInSessionId;

			// grab first user message text
			if (firstUserMessage == null && msg.Type == "user" && msg.Message?.Content != null)
			{
				var text = ExtractTextContent(msg.Message.Content.Value);
				if (!string.IsNullOrWhiteSpace(text))
					firstUserMessage = text;
			}
		}

		var isEmpty = firstUserMessage == null;
		firstUserMessage ??= "{empty}";

		// unnamed sessions are shown by their short id, like Claude's resume list
		var fallbackTitle = sessionId.Length > 8 ? sessionId[..8] : sessionId;
		var title = customTitle ?? aiTitle ?? slugTitle ?? fallbackTitle;
		timestamp ??= File.GetCreationTime(filePath);

		// truncate long messages for display
		if (firstUserMessage.Length > 120)
			firstUserMessage = firstUserMessage[..120] + "...";

		// collapse newlines for single-line display
		firstUserMessage = firstUserMessage.ReplaceLineEndings(" ");

		return new ConversationInfo(filePath, title, timestamp.Value, firstUserMessage)
		{
			ContinuedInSessionId = continuedIn,
			SessionId = sessionId,
			IsEmpty = isEmpty,
		};
	}

	private static string ExtractTextContent(JsonElement content)
	{
		// content can be a string or an array of content blocks
		if (content.ValueKind == JsonValueKind.String)
		{
			var s = content.GetString() ?? "";
			return s.TrimStart().StartsWith('<') ? "" : s;
		}

		if (content.ValueKind == JsonValueKind.Array)
		{
			foreach (var block in content.EnumerateArray())
			{
				if (block.TryGetProperty("type", out var type) && type.GetString() == "text"
					&& block.TryGetProperty("text", out var text))
				{
					var s = text.GetString() ?? "";
					// skip system-injected content blocks (e.g. <ide_selection>, <system-reminder>)
					if (!string.IsNullOrWhiteSpace(s) && !s.TrimStart().StartsWith('<'))
						return s;
				}
			}
		}

		return "";
	}

	private static string FormatSlug(string slug)
	{
		// "proud-tinkering-tiger" -> "Proud Tinkering Tiger"
		return string.Join(' ', slug.Split('-').Select(w =>
			w.Length > 0 ? char.ToUpper(w[0]) + w[1..] : w));
	}

	private static DateTime? ParseTimestamp(string? ts)
	{
		if (ts == null) return null;
		return DateTime.TryParse(ts, out var dt) ? dt.ToLocalTime() : null;
	}

	public static void RenameConversation(ConversationInfo conv, string newTitle)
	{
		var title = newTitle.Trim();
		if (title.Length == 0)
			return;

		// name the live session, not the superseded file Claude continued from
		var target = ResolveChainHead(conv);

		var sessionDir = Path.ChangeExtension(target, null)
			?? throw new InvalidOperationException("Invalid conversation path.");
		var sessionId = Path.GetFileNameWithoutExtension(target);

		// mirror the files Claude Code's own /rename writes
		Directory.CreateDirectory(sessionDir);
		WriteCustomTitle(Path.Combine(sessionDir, "custom-title.json"), title);
		AppendCustomTitleEvent(target, sessionId, title);
	}

	private static string ResolveChainHead(ConversationInfo conv)
	{
		var current = conv.FilePath;
		var nextId = conv.ContinuedInSessionId;
		var projectDir = Path.GetDirectoryName(current);
		var seen = new HashSet<string>(StringComparer.Ordinal) { current };

		while (!string.IsNullOrEmpty(nextId) && projectDir != null && Path.GetFileName(nextId) == nextId)
		{
			var next = Path.Combine(projectDir, nextId + ".jsonl");
			if (!File.Exists(next) || !seen.Add(next))
				break;

			current = next;
			nextId = ReadContinuedIn(current);
		}

		return current;
	}

	private static string? ReadContinuedIn(string filePath)
	{
		try
		{
			foreach (var line in File.ReadLines(filePath))
			{
				if (!line.Contains("\"continuedInSessionId\"", StringComparison.Ordinal))
					continue;

				var msg = JsonSerializer.Deserialize(line, AppJsonContext.Default.JsonlMessage);
				if (msg != null && !string.IsNullOrEmpty(msg.ContinuedInSessionId))
					return msg.ContinuedInSessionId;
			}
		}
		catch
		{
			// ignore unreadable continuation links
		}

		return null;
	}

	private static string? ReadCustomTitle(string filePath)
	{
		var sessionDir = Path.ChangeExtension(filePath, null);
		if (sessionDir == null)
			return null;

		var titleFile = Path.Combine(sessionDir, "custom-title.json");

		try
		{
			if (!File.Exists(titleFile))
				return null;

			using var doc = JsonDocument.Parse(File.ReadAllText(titleFile));
			if (doc.RootElement.ValueKind == JsonValueKind.Object
				&& doc.RootElement.TryGetProperty("customTitle", out var value)
				&& value.ValueKind == JsonValueKind.String)
				return value.GetString();
		}
		catch
		{
			// ignore a corrupt title file
		}

		return null;
	}

	private static void WriteCustomTitle(string path, string title)
	{
		var json = new JsonObject { ["customTitle"] = title }.ToJsonString();
		var tmp = path + ".tmp";
		File.WriteAllText(tmp, json);
		File.Move(tmp, path, overwrite: true);
	}

	private static void AppendCustomTitleEvent(string filePath, string sessionId, string title)
	{
		var line = new JsonObject
		{
			["type"] = "custom-title",
			["customTitle"] = title,
			["sessionId"] = sessionId,
		}.ToJsonString();

		bool needsNewline = false;
		using (var read = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
		{
			if (read.Length > 0)
			{
				read.Seek(-1, SeekOrigin.End);
				needsNewline = read.ReadByte() != '\n';
			}
		}

		using var stream = new FileStream(filePath, FileMode.Append, FileAccess.Write, FileShare.ReadWrite);
		using var writer = new StreamWriter(stream);
		if (needsNewline)
			writer.WriteLine();
		writer.WriteLine(line);
	}

	public static void DeleteConversation(ConversationInfo conv)
	{
		var current = conv.FilePath;
		var nextId = conv.ContinuedInSessionId;
		var projectDir = Path.GetDirectoryName(current);
		var seen = new HashSet<string>(StringComparer.Ordinal);

		// a conversation can span several files linked by continued-in
		while (seen.Add(current))
		{
			DeleteSessionFiles(current);

			if (string.IsNullOrEmpty(nextId) || projectDir == null || Path.GetFileName(nextId) != nextId)
				break;

			var next = Path.Combine(projectDir, nextId + ".jsonl");
			if (!File.Exists(next))
				break;

			current = next;
			nextId = ReadContinuedIn(current);
		}
	}

	private static void DeleteSessionFiles(string filePath)
	{
		// delete the .jsonl file
		if (File.Exists(filePath))
			File.Delete(filePath);

		// delete companion directory (subagents, custom title etc.) if it exists
		var companionDir = Path.ChangeExtension(filePath, null);
		if (companionDir != null && Directory.Exists(companionDir))
			Directory.Delete(companionDir, recursive: true);
	}
}
