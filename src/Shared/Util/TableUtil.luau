--!nonstrict
local TableUtil = {}

function TableUtil.DeepCopy(t)
	if type(t) ~= "table" then
		return t
	end
	local out = {}
	for k, v in pairs(t) do
		out[k] = TableUtil.DeepCopy(v)
	end
	return out
end

-- Aggiunge le chiavi mancanti del template al target (ricorsivo), senza sovrascrivere i valori esistenti.
function TableUtil.Reconcile(target, template)
	for k, v in pairs(template) do
		if target[k] == nil then
			target[k] = TableUtil.DeepCopy(v)
		elseif type(v) == "table" and type(target[k]) == "table" and not TableUtil.IsArray(v) then
			TableUtil.Reconcile(target[k], v)
		end
	end
	return target
end

function TableUtil.IsArray(t)
	if type(t) ~= "table" then
		return false
	end
	local n = #t
	if n == 0 then
		return next(t) == nil
	end
	return next(t, n) == nil
end

function TableUtil.Count(t)
	local n = 0
	for _ in pairs(t) do
		n += 1
	end
	return n
end

function TableUtil.Keys(t)
	local out = {}
	for k in pairs(t) do
		table.insert(out, k)
	end
	return out
end

function TableUtil.Values(t)
	local out = {}
	for _, v in pairs(t) do
		table.insert(out, v)
	end
	return out
end

function TableUtil.Find(t, predicate)
	for k, v in pairs(t) do
		if predicate(v, k) then
			return v, k
		end
	end
	return nil
end

function TableUtil.Filter(t, predicate)
	local out = {}
	for _, v in ipairs(t) do
		if predicate(v) then
			table.insert(out, v)
		end
	end
	return out
end

function TableUtil.Map(t, fn)
	local out = {}
	for i, v in ipairs(t) do
		out[i] = fn(v, i)
	end
	return out
end

-- Shuffle deterministico con Random fornito
function TableUtil.Shuffle(t, rng)
	rng = rng or Random.new()
	for i = #t, 2, -1 do
		local j = rng:NextInteger(1, i)
		t[i], t[j] = t[j], t[i]
	end
	return t
end

function TableUtil.Truncate(list, maxLen)
	while #list > maxLen do
		table.remove(list, 1)
	end
	return list
end

return TableUtil
