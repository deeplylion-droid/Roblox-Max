--!nonstrict
-- Validazione difensiva degli argomenti ricevuti dai client.
local Guard = {}

function Guard.Int(v, min, max)
	if type(v) ~= "number" or v ~= v or v ~= math.floor(v) then
		return nil
	end
	if min and v < min then
		return nil
	end
	if max and v > max then
		return nil
	end
	return v
end

function Guard.Str(v, maxLen)
	if type(v) ~= "string" then
		return nil
	end
	if maxLen and #v > maxLen then
		return nil
	end
	return v
end

function Guard.Bool(v)
	if type(v) ~= "boolean" then
		return nil
	end
	return v
end

function Guard.Table(v)
	if type(v) ~= "table" then
		return nil
	end
	return v
end

return Guard
