--!nonstrict
--[[
	Store: wrapper sui DataStore con retry, backoff e fallback in memoria
	(Studio senza accesso API o errori persistenti). Tutti gli accessi passano da qui.
]]
local DataStoreService = game:GetService("DataStoreService")
local RunService = game:GetService("RunService")
local Logger = require(script.Parent.Logger)

local Store = {}
Store.__index = Store

local MAX_RETRIES = 4
local mockStores = {}
local apiAvailable = nil

local function checkApi()
	if apiAvailable ~= nil then
		return apiAvailable
	end
	local ok, err = pcall(function()
		return DataStoreService:GetDataStore("__vivaio_probe"):GetAsync("probe")
	end)
	if ok then
		apiAvailable = true
	else
		local msg = tostring(err)
		-- 403 = API non abilitata in Studio; usiamo lo store in memoria
		apiAvailable = not (msg:find("403") or msg:find("not enabled") or msg:find("Studio access") or msg:find("API Services"))
		if not apiAvailable then
			Logger.Warn("Store", "DataStore non disponibile (" .. msg .. "). Uso store in memoria: i dati NON saranno salvati.")
		end
	end
	return apiAvailable
end

function Store.new(name)
	local self = setmetatable({ Name = name }, Store)
	if checkApi() then
		self._ds = DataStoreService:GetDataStore(name)
	else
		mockStores[name] = mockStores[name] or {}
		self._mock = mockStores[name]
	end
	return self
end

function Store:IsMock()
	return self._mock ~= nil
end

local function withRetry(fn, label)
	local delay = 1
	local lastErr
	for attempt = 1, MAX_RETRIES do
		local ok, result = pcall(fn)
		if ok then
			return true, result
		end
		lastErr = result
		Logger.Warn("Store", label, "tentativo", attempt, "fallito:", result)
		task.wait(delay)
		delay *= 2
	end
	return false, lastErr
end

function Store:Get(key)
	if self._mock then
		local v = self._mock[key]
		return true, v
	end
	return withRetry(function()
		return self._ds:GetAsync(key)
	end, "Get " .. key)
end

-- transform(old) -> new (o nil per annullare)
function Store:Update(key, transform)
	if self._mock then
		local ok, result = pcall(transform, self._mock[key])
		if not ok then
			return false, result
		end
		if result ~= nil then
			self._mock[key] = result
		end
		return true, self._mock[key]
	end
	return withRetry(function()
		return self._ds:UpdateAsync(key, transform)
	end, "Update " .. key)
end

function Store:Set(key, value)
	if self._mock then
		self._mock[key] = value
		return true
	end
	return withRetry(function()
		self._ds:SetAsync(key, value)
		return true
	end, "Set " .. key)
end

function Store:Remove(key)
	if self._mock then
		self._mock[key] = nil
		return true
	end
	return withRetry(function()
		self._ds:RemoveAsync(key)
		return true
	end, "Remove " .. key)
end

Store.IsStudio = RunService:IsStudio()

return Store
