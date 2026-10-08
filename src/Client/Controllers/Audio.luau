--!nonstrict
-- Effetti sonori (asset integrati Roblox) con interruttore audio.
local SoundService = game:GetService("SoundService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Net = require(ReplicatedStorage.Shared.Util.Net)

local Audio = { Enabled = true }
local sounds = {}
local group

local VOLUMES = { Collect = 0.5, Deposit = 0.6, Click = 0.35, Place = 0.5, Error = 0.4, Success = 0.6, Whoosh = 0.5, Splash = 0.5, Sentinel = 0.5, Chime = 0.5 }

function Audio.Init()
	group = Instance.new("SoundGroup")
	group.Name = "VivaioSFX"
	group.Volume = 1
	group.Parent = SoundService
	for key, id in pairs(Config.Sounds) do
		local s = Instance.new("Sound")
		s.Name = key
		s.SoundId = id
		s.Volume = VOLUMES[key] or 0.5
		s.SoundGroup = group
		s.Parent = group
		sounds[key] = s
	end
	Net.Event("PlaySound").OnClientEvent:Connect(function(key)
		Audio.Play(key)
	end)
end

function Audio.Play(key, pitch)
	if not Audio.Enabled then
		return
	end
	local s = sounds[key]
	if not s then
		return
	end
	local clone = s:Clone()
	clone.PlaybackSpeed = pitch or (0.95 + math.random() * 0.1)
	clone.Parent = group
	clone:Play()
	clone.Ended:Once(function()
		clone:Destroy()
	end)
	task.delay(6, function()
		if clone.Parent then
			clone:Destroy()
		end
	end)
end

function Audio.SetEnabled(enabled)
	Audio.Enabled = enabled
	if group then
		group.Volume = enabled and 1 or 0
	end
end

return Audio
