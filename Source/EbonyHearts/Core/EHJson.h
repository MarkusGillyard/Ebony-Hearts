// Minimal JSON reader for combat data. Engine-independent so the combat core can be tested without Unreal.
#pragma once

#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <vector>

namespace eh
{
class JsonValue
{
public:
	enum class Kind : uint8_t { Null, Bool, Number, String, Array, Object };

	Kind kind = Kind::Null;
	bool boolean = false;
	double number = 0.0;
	std::string text;
	std::vector<JsonValue> items;
	std::vector<std::pair<std::string, JsonValue>> members;   // keeps file order for stable error messages

	bool IsObject() const { return kind == Kind::Object; }
	bool IsArray() const { return kind == Kind::Array; }
	bool IsNumber() const { return kind == Kind::Number; }
	bool IsString() const { return kind == Kind::String; }
	bool IsBool() const { return kind == Kind::Bool; }

	// Returns nullptr when the member is absent or this is not an object.
	const JsonValue* Find(const std::string& key) const;
};

// Parses UTF-8 JSON text. On failure returns false and fills error with "line:column: reason".
bool ParseJson(const std::string& source, JsonValue& out, std::string& error);
}
