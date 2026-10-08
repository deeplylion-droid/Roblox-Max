--!nonstrict
local TimeUtil = {}

-- Chiave del giorno UTC (es. "2026-10-07"); le commissioni si rinnovano a mezzanotte UTC.
function TimeUtil.DayKey(t)
	t = t or os.time()
	return os.date("!%Y-%m-%d", t)
end

function TimeUtil.SecondsToNextDay(t)
	t = t or os.time()
	local d = os.date("!*t", t)
	local elapsed = d.hour * 3600 + d.min * 60 + d.sec
	return 86400 - elapsed
end

-- Numero della settimana (dal lunedì) usato per i temi settimanali
function TimeUtil.WeekIndex(t)
	t = t or os.time()
	-- 1970-01-01 era un giovedì; spostiamo di 3 giorni per allineare al lunedì
	return math.floor((t + 3 * 86400) / (7 * 86400))
end

function TimeUtil.SecondsToNextWeek(t)
	t = t or os.time()
	local weekStart = (TimeUtil.WeekIndex(t) * 7 * 86400) - 3 * 86400
	return weekStart + 7 * 86400 - t
end

-- Hash deterministico (FNV-1a) di una stringa → intero positivo, per semi riproducibili
function TimeUtil.Hash(str)
	local h = 2166136261
	for i = 1, #str do
		h = bit32.bxor(h, string.byte(str, i))
		h = (h * 16777619) % 4294967296
	end
	return h
end

return TimeUtil
