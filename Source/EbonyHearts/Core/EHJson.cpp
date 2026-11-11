#include "EHJson.h"

#include <cstdlib>

namespace eh
{
const JsonValue* JsonValue::Find(const std::string& key) const
{
	if (kind != Kind::Object)
	{
		return nullptr;
	}
	for (const auto& member : members)
	{
		if (member.first == key)
		{
			return &member.second;
		}
	}
	return nullptr;
}

namespace jsonparse
{
struct Reader
{
	const std::string& src;
	size_t pos = 0;
	std::string error;
	int depth = 0;

	explicit Reader(const std::string& source) : src(source) {}

	bool Fail(const std::string& reason)
	{
		if (error.empty())
		{
			int line = 1;
			int column = 1;
			for (size_t i = 0; i < pos && i < src.size(); ++i)
			{
				if (src[i] == '\n')
				{
					++line;
					column = 1;
				}
				else
				{
					++column;
				}
			}
			error = std::to_string(line) + ":" + std::to_string(column) + ": " + reason;
		}
		return false;
	}

	void SkipSpace()
	{
		while (pos < src.size())
		{
			const char c = src[pos];
			if (c == ' ' || c == '\t' || c == '\n' || c == '\r')
			{
				++pos;
			}
			else
			{
				break;
			}
		}
	}

	bool Literal(const char* word, size_t length)
	{
		if (src.compare(pos, length, word) != 0)
		{
			return Fail("unexpected token");
		}
		pos += length;
		return true;
	}

	bool ParseString(std::string& out)
	{
		++pos;   // opening quote
		out.clear();
		while (pos < src.size())
		{
			const char c = src[pos++];
			if (c == '"')
			{
				return true;
			}
			if (static_cast<unsigned char>(c) < 0x20)
			{
				return Fail("control character in string");
			}
			if (c != '\\')
			{
				out.push_back(c);
				continue;
			}
			if (pos >= src.size())
			{
				break;
			}
			const char e = src[pos++];
			switch (e)
			{
			case '"': out.push_back('"'); break;
			case '\\': out.push_back('\\'); break;
			case '/': out.push_back('/'); break;
			case 'b': out.push_back('\b'); break;
			case 'f': out.push_back('\f'); break;
			case 'n': out.push_back('\n'); break;
			case 'r': out.push_back('\r'); break;
			case 't': out.push_back('\t'); break;
			case 'u':
			{
				if (pos + 4 > src.size())
				{
					return Fail("short unicode escape");
				}
				unsigned code = 0;
				for (int i = 0; i < 4; ++i)
				{
					const char h = src[pos++];
					code <<= 4;
					if (h >= '0' && h <= '9') code |= static_cast<unsigned>(h - '0');
					else if (h >= 'a' && h <= 'f') code |= static_cast<unsigned>(h - 'a' + 10);
					else if (h >= 'A' && h <= 'F') code |= static_cast<unsigned>(h - 'A' + 10);
					else return Fail("bad unicode escape");
				}
				// Data files are ASCII in practice; encode BMP code points as UTF-8.
				if (code < 0x80)
				{
					out.push_back(static_cast<char>(code));
				}
				else if (code < 0x800)
				{
					out.push_back(static_cast<char>(0xC0 | (code >> 6)));
					out.push_back(static_cast<char>(0x80 | (code & 0x3F)));
				}
				else
				{
					out.push_back(static_cast<char>(0xE0 | (code >> 12)));
					out.push_back(static_cast<char>(0x80 | ((code >> 6) & 0x3F)));
					out.push_back(static_cast<char>(0x80 | (code & 0x3F)));
				}
				break;
			}
			default:
				return Fail("bad escape");
			}
		}
		return Fail("unterminated string");
	}

	bool ParseValue(JsonValue& out)
	{
		SkipSpace();
		if (pos >= src.size())
		{
			return Fail("unexpected end of input");
		}
		if (++depth > 64)
		{
			return Fail("nesting too deep");
		}
		bool ok = true;
		const char c = src[pos];
		if (c == '{')
		{
			out.kind = JsonValue::Kind::Object;
			++pos;
			SkipSpace();
			if (pos < src.size() && src[pos] == '}')
			{
				++pos;
			}
			else
			{
				for (;;)
				{
					SkipSpace();
					if (pos >= src.size() || src[pos] != '"')
					{
						ok = Fail("expected member name");
						break;
					}
					std::string key;
					if (!ParseString(key))
					{
						ok = false;
						break;
					}
					for (const auto& existing : out.members)
					{
						if (existing.first == key)
						{
							ok = Fail("duplicate member \"" + key + "\"");
							break;
						}
					}
					if (!ok)
					{
						break;
					}
					SkipSpace();
					if (pos >= src.size() || src[pos] != ':')
					{
						ok = Fail("expected ':'");
						break;
					}
					++pos;
					out.members.emplace_back(key, JsonValue());
					if (!ParseValue(out.members.back().second))
					{
						ok = false;
						break;
					}
					SkipSpace();
					if (pos < src.size() && src[pos] == ',')
					{
						++pos;
						continue;
					}
					if (pos < src.size() && src[pos] == '}')
					{
						++pos;
						break;
					}
					ok = Fail("expected ',' or '}'");
					break;
				}
			}
		}
		else if (c == '[')
		{
			out.kind = JsonValue::Kind::Array;
			++pos;
			SkipSpace();
			if (pos < src.size() && src[pos] == ']')
			{
				++pos;
			}
			else
			{
				for (;;)
				{
					out.items.emplace_back();
					if (!ParseValue(out.items.back()))
					{
						ok = false;
						break;
					}
					SkipSpace();
					if (pos < src.size() && src[pos] == ',')
					{
						++pos;
						continue;
					}
					if (pos < src.size() && src[pos] == ']')
					{
						++pos;
						break;
					}
					ok = Fail("expected ',' or ']'");
					break;
				}
			}
		}
		else if (c == '"')
		{
			out.kind = JsonValue::Kind::String;
			ok = ParseString(out.text);
		}
		else if (c == 't')
		{
			out.kind = JsonValue::Kind::Bool;
			out.boolean = true;
			ok = Literal("true", 4);
		}
		else if (c == 'f')
		{
			out.kind = JsonValue::Kind::Bool;
			out.boolean = false;
			ok = Literal("false", 5);
		}
		else if (c == 'n')
		{
			out.kind = JsonValue::Kind::Null;
			ok = Literal("null", 4);
		}
		else if (c == '-' || (c >= '0' && c <= '9'))
		{
			const size_t start = pos;
			if (src[pos] == '-')
			{
				++pos;
			}
			while (pos < src.size())
			{
				const char d = src[pos];
				if ((d >= '0' && d <= '9') || d == '.' || d == 'e' || d == 'E' || d == '+' || d == '-')
				{
					++pos;
				}
				else
				{
					break;
				}
			}
			const std::string token = src.substr(start, pos - start);
			char* end = nullptr;
			out.kind = JsonValue::Kind::Number;
			out.number = std::strtod(token.c_str(), &end);
			if (end == nullptr || *end != '\0' || token == "-")
			{
				pos = start;
				ok = Fail("malformed number");
			}
		}
		else
		{
			ok = Fail("unexpected character");
		}
		--depth;
		return ok;
	}
};
}

bool ParseJson(const std::string& source, JsonValue& out, std::string& error)
{
	jsonparse::Reader reader(source);
	out = JsonValue();
	if (!reader.ParseValue(out))
	{
		error = reader.error;
		return false;
	}
	reader.SkipSpace();
	if (reader.pos != source.size())
	{
		reader.Fail("trailing characters after value");
		error = reader.error;
		return false;
	}
	return true;
}
}
