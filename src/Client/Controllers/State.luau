--!nonstrict
-- Stato replicato dal server (sezioni del profilo). Changed(key, value) per aggiornare la UI.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Net = require(Shared.Util.Net)
local Signal = require(Shared.Util.Signal)

local State = { Data = {}, Changed = Signal.new(), Ready = Signal.new(), IsReady = false }

function State.Get(key)
	return State.Data[key]
end

function State.Init()
	Net.Event("StateSync").OnClientEvent:Connect(function(payload)
		for k, v in pairs(payload) do
			State.Data[k] = v
			State.Changed:Fire(k, v)
		end
	end)
	-- stato iniziale completo (riprova finché il profilo non è caricato)
	task.spawn(function()
		local tries = 0
		while not State.IsReady do
			tries += 1
			local ok, full = pcall(function()
				return Net.Function("GetState"):InvokeServer()
			end)
			if ok and full then
				for k, v in pairs(full) do
					State.Data[k] = v
				end
				State.IsReady = true
				for k, v in pairs(full) do
					State.Changed:Fire(k, v)
				end
				State.Ready:Fire()
				Net.Fire("ClientReady")
			else
				task.wait(math.min(5, 0.5 * tries))
			end
		end
	end)
end

function State.OnReady(fn)
	if State.IsReady then
		task.spawn(fn)
	else
		State.Ready:Once(fn)
	end
end

-- Osserva una chiave: chiama subito se già presente, poi a ogni cambio
function State.Observe(key, fn)
	if State.Data[key] ~= nil then
		task.spawn(fn, State.Data[key])
	end
	return State.Changed:Connect(function(k, v)
		if k == key then
			fn(v)
		end
	end)
end

return State
