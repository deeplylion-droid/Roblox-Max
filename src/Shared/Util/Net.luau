--!nonstrict
-- Accesso ai remoti lato client/server.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local RemoteList = require(script.Parent.Parent.Remotes)

local Net = {}
local folder

local function getFolder()
	if folder then
		return folder
	end
	if RunService:IsServer() then
		folder = ReplicatedStorage:FindFirstChild("Remotes")
		if not folder then
			folder = Instance.new("Folder")
			folder.Name = "Remotes"
			for _, name in ipairs(RemoteList.Events) do
				local ev = Instance.new("RemoteEvent")
				ev.Name = name
				ev.Parent = folder
			end
			for _, name in ipairs(RemoteList.Functions) do
				local fn = Instance.new("RemoteFunction")
				fn.Name = name
				fn.Parent = folder
			end
			folder.Parent = ReplicatedStorage
		end
	else
		folder = ReplicatedStorage:WaitForChild("Remotes")
	end
	return folder
end

function Net.Event(name): RemoteEvent
	local f = getFolder()
	local r = RunService:IsServer() and f:FindFirstChild(name) or f:WaitForChild(name)
	assert(r, "Remote event mancante: " .. name)
	return r
end

function Net.Function(name): RemoteFunction
	local f = getFolder()
	local r = RunService:IsServer() and f:FindFirstChild(name) or f:WaitForChild(name)
	assert(r, "Remote function mancante: " .. name)
	return r
end

-- Client: invoca con pcall e timeout morbido
function Net.Invoke(name, ...)
	local ok, a, b, c = pcall(function(...)
		return Net.Function(name):InvokeServer(...)
	end, ...)
	if not ok then
		warn("[Net] Invoke fallita", name, a)
		return false, "Errore di rete"
	end
	return a, b, c
end

function Net.Fire(name, ...)
	Net.Event(name):FireServer(...)
end

return Net
