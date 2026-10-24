using System.Text.Json;
using System.Text.Json.Serialization;

namespace ClaudeChatManager;

// Only the fields we need from the JSONL lines
public class JsonlMessage
{
	[JsonPropertyName("type")]
	public string? Type { get; set; }

	[JsonPropertyName("message")]
	public MessageContent? Message { get; set; }

	[JsonPropertyName("timestamp")]
	public string? Timestamp { get; set; }

	[JsonPropertyName("uuid")]
	public string? Uuid { get; set; }

	[JsonPropertyName("slug")]
	public string? Slug { get; set; }

	[JsonPropertyName("aiTitle")]
	public string? AiTitle { get; set; }

	[JsonPropertyName("customTitle")]
	public string? CustomTitle { get; set; }

	[JsonPropertyName("continuedInSessionId")]
	public string? ContinuedInSessionId { get; set; }
}

public class MessageContent
{
	[JsonPropertyName("role")]
	public string? Role { get; set; }

	[JsonPropertyName("content")]
	public JsonElement? Content { get; set; }
}

// Our display models
public record ProjectInfo(string Name, string Path);

public record ConversationInfo(
	string FilePath,
	string Title,
	DateTime Date,
	string FirstMessage)
{
	public string? ContinuedInSessionId { get; init; }

	// the live session (continuation head); FilePath may point at an older link
	public string SessionId { get; init; } = "";

	public bool IsEmpty { get; init; }

	public string Id => SessionId.Length > 0 ? SessionId : Path.GetFileNameWithoutExtension(FilePath);

	public string ShortId => Id.Length > 8 ? Id[..8] : Id;
}

[JsonSerializable(typeof(JsonlMessage))]
[JsonSourceGenerationOptions(PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase)]
public partial class AppJsonContext : JsonSerializerContext;
