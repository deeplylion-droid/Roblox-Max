--!nonstrict
--[[
	RaidController: fisica "di sensazione" lato client (il personaggio è di proprietà del client):
	spinta delle correnti d'aria, trampolini di luce della cupola, nebbia locale.
	Il server verifica solo gli esiti (pozza raggiunta, uscita, sentinelle, cadute).
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Net = require(ReplicatedStorage.Shared.Util.Net)

local RaidController = {}
local player = Players.LocalPlayer
local zones = {} -- part -> true
local pads = {}
local fogZones = {}
local lastBounce = 0
local baseFogEnd

local function track(inst)
	if inst:IsA("BasePart") then
		if inst.Name == "Zone" and inst:GetAttribute("Push") then
			zones[inst] = true
		elseif inst.Name == "BouncePad" then
			pads[inst] = true
		elseif inst.Name == "FogZone" then
			fogZones[inst] = true
		end
	end
end

local function untrack(inst)
	zones[inst] = nil
	pads[inst] = nil
	fogZones[inst] = nil
end

local function inside(part, pos, margin)
	local lp = part.CFrame:PointToObjectSpace(pos)
	local h = part.Size / 2 + Vector3.new(margin or 0, margin or 0, margin or 0)
	return math.abs(lp.X) <= h.X and math.abs(lp.Y) <= h.Y and math.abs(lp.Z) <= h.Z
end

function RaidController.Init(onEvent)
	for _, folderName in ipairs({ "Plots", "Arenas", "World" }) do
		local f = Workspace:WaitForChild(folderName, 30)
		if f then
			for _, d in ipairs(f:GetDescendants()) do
				track(d)
			end
			f.DescendantAdded:Connect(track)
			f.DescendantRemoving:Connect(untrack)
		end
	end
	baseFogEnd = Lighting.FogEnd

	Net.Event("RaidEvent").OnClientEvent:Connect(function(name, payload)
		if onEvent then
			onEvent(name, payload or {})
		end
	end)

	RunService.Heartbeat:Connect(function(dt)
		local char = player.Character
		local hrp = char and char:FindFirstChild("HumanoidRootPart")
		local hum = char and char:FindFirstChildOfClass("Humanoid")
		if not hrp or not hum then
			return
		end
		local pos = hrp.Position
		-- correnti d'aria
		for zone in pairs(zones) do
			if zone.Parent and zone:GetAttribute("Active") ~= false and inside(zone, pos, 0.5) then
				local push = zone:GetAttribute("Push") or 55
				local dir = zone:GetAttribute("Dir") or 1
				local v
				if zone:GetAttribute("Up") then
					v = Vector3.new(0, push * 0.9, 0)
				else
					v = zone.CFrame.RightVector * push * dir
				end
				-- accelerazione dolce ma decisa (telegrafata dalle particelle)
				hrp.AssemblyLinearVelocity = hrp.AssemblyLinearVelocity:Lerp(Vector3.new(v.X, hrp.AssemblyLinearVelocity.Y + v.Y * dt, v.Z), math.clamp(dt * 6, 0, 1))
			end
		end
		-- trampolini
		if os.clock() - lastBounce > 0.4 then
			for pad in pairs(pads) do
				if pad.Parent then
					local rel = pos - pad.Position
					if Vector3.new(rel.X, 0, rel.Z).Magnitude <= pad.Size.Y / 2 + 0.6 and rel.Y > 0 and rel.Y < 5 and hum.FloorMaterial ~= Enum.Material.Air then
						local power = pad:GetAttribute("Bounce") or 90
						hrp.AssemblyLinearVelocity = Vector3.new(hrp.AssemblyLinearVelocity.X * 0.4, power, hrp.AssemblyLinearVelocity.Z * 0.4)
						lastBounce = os.clock()
						break
					end
				end
			end
		end
		-- nebbia locale
		local inFog = false
		for fz in pairs(fogZones) do
			if fz.Parent and inside(fz, pos, 1) then
				inFog = true
				break
			end
		end
		local targetEnd = inFog and 45 or baseFogEnd
		if math.abs(Lighting.FogEnd - targetEnd) > 1 then
			Lighting.FogEnd = Lighting.FogEnd + (targetEnd - Lighting.FogEnd) * math.clamp(dt * 3, 0, 1)
		end
	end)
end

return RaidController
