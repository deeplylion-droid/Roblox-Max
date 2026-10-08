--!nonstrict
local Format = {}

function Format.Number(n)
	n = math.floor(n + 0.5)
	if n >= 1_000_000 then
		return string.format("%.1fM", n / 1_000_000)
	elseif n >= 10_000 then
		return string.format("%.1fk", n / 1000)
	end
	-- separatore migliaia con punto (stile italiano)
	local s = tostring(n)
	local formatted = s:reverse():gsub("(%d%d%d)", "%1."):reverse()
	if formatted:sub(1, 1) == "." then
		formatted = formatted:sub(2)
	end
	return formatted
end

function Format.Time(seconds)
	seconds = math.max(0, math.floor(seconds))
	local h = seconds // 3600
	local m = (seconds % 3600) // 60
	local s = seconds % 60
	if h > 0 then
		return string.format("%dh %02dm", h, m)
	end
	return string.format("%d:%02d", m, s)
end

function Format.Percent(x)
	return string.format("%d%%", math.floor(x * 100 + 0.5))
end

function Format.Stars(n, max)
	max = max or 5
	local s = ""
	for i = 1, max do
		s ..= (i <= n) and "●" or "○"
	end
	return s
end

return Format
