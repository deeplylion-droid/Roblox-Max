--!nonstrict
--[[
	WorldAnimator: animazioni cosmetiche lato client (le parti sono ancorate: muoverle
	localmente non costa rete). Creature (bob/hop/orbit/drift), sentinelle e piattaforme
	fuori dalle arene, girandole, lanterne, portale, albero. LOD per distanza e
	modalità effetti ridotti.
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local ModuleModel = require(ReplicatedStorage.Shared.Models.ModuleModel)

local Animator = { Reduced = false }
local creatures = {} -- model -> data
local spinners = {} -- part -> kind
local sentinels = {} -- model -> data
local platforms = {} -- part -> data
local camera = Workspace.CurrentCamera
local emitters = {} -- emitter -> originalEnabled
local CELL = Config.Grid.CellSize
local LOD_DISTANCE = 220

local function isRaidArena(inst)
	local v = inst:FindFirstAncestor("Vivaio")
	return v and v:GetAttribute("Mode") == "raid"
end

local function register(inst)
	if inst:IsA("Model") then
		if inst:GetAttribute("CreatureId") and inst.PrimaryPart then
			creatures[inst] = { Base = inst:GetPivot(), Phase = math.random() * math.pi * 2, Behavior = inst:GetAttribute("Behavior") or "bob" }
		elseif inst:GetAttribute("ModuleId") == "sentinella" then
			task.defer(function()
				local cone = inst:FindFirstChild("Cone")
				if cone and inst.PrimaryPart and not isRaidArena(inst) then
					sentinels[inst] = { Cone = cone, Base = inst.PrimaryPart.Position, Radius = cone:GetAttribute("Radius") or 9, Speed = cone:GetAttribute("Speed") or 55, Offset = math.random() * 360 }
				end
			end)
		elseif inst:GetAttribute("ModuleId") == "piattaforma" then
			task.defer(function()
				if isRaidArena(inst) or not inst.PrimaryPart then
					return
				end
				for _, name in ipairs({ "Platform", "Platform2" }) do
					local p = inst:FindFirstChild(name)
					if p then
						platforms[p] = { Root = inst.PrimaryPart, Period = p:GetAttribute("Period") or 3.2, Travel = p:GetAttribute("Travel") or 8, Phase = p:GetAttribute("Phase") or 0 }
					end
				end
			end)
		end
	elseif inst:IsA("BasePart") then
		local anim = inst:GetAttribute("Anim")
		if anim then
			spinners[inst] = { Kind = anim, Base = inst.CFrame, Phase = math.random() * math.pi * 2, Children = {} }
			if anim == "spin" and inst.Parent then
				for _, c in ipairs(inst.Parent:GetChildren()) do
					if c:IsA("BasePart") and c:GetAttribute("SpinChild") then
						table.insert(spinners[inst].Children, { Part = c, Offset = inst.CFrame:ToObjectSpace(c.CFrame) })
					end
				end
			end
		end
	elseif inst:IsA("ParticleEmitter") then
		emitters[inst] = inst.Enabled
		if Animator.Reduced then
			inst.Enabled = false
		end
	end
end

local function unregister(inst)
	creatures[inst] = nil
	spinners[inst] = nil
	sentinels[inst] = nil
	platforms[inst] = nil
	emitters[inst] = nil
end

local function creatureOffset(data, t)
	local b = data.Behavior
	local p = data.Phase
	if b == "hop" then
		local cycle = (t * 1.6 + p) % (math.pi * 2)
		local h = math.max(0, math.sin(cycle)) * 2.2
		local squash = 1 - math.max(0, -math.sin(cycle)) * 0.15
		return CFrame.new(0, h, 0) * CFrame.Angles(0, math.sin(t * 0.3 + p) * 0.3, 0), squash
	elseif b == "orbit" then
		local a = t * 0.8 + p
		return CFrame.new(math.cos(a) * 1.2, math.sin(t * 2 + p) * 0.25, math.sin(a) * 1.2) * CFrame.Angles(0, -a + math.pi / 2, 0), 1
	elseif b == "drift" then
		local a = t * 0.5 + p
		return CFrame.new(math.sin(a) * 1.4, math.sin(t * 1.3 + p) * 0.4, math.sin(a * 2) * 0.7) * CFrame.Angles(0, math.sin(a) * 0.5, math.cos(a) * 0.08), 1
	end
	return CFrame.new(0, math.sin(t * 1.8 + p) * 0.35, 0) * CFrame.Angles(0, math.sin(t * 0.4 + p) * 0.4, 0), 1
end

function Animator.SetReduced(reduced)
	Animator.Reduced = reduced
	for e, original in pairs(emitters) do
		if e.Parent then
			e.Enabled = if reduced then false else original
		end
	end
end

function Animator.Init()
	for _, folderName in ipairs({ "Plots", "Arenas", "World" }) do
		local f = Workspace:WaitForChild(folderName, 30)
		if f then
			for _, d in ipairs(f:GetDescendants()) do
				register(d)
			end
			f.DescendantAdded:Connect(register)
			f.DescendantRemoving:Connect(unregister)
		end
	end
	local frame = 0
	RunService.RenderStepped:Connect(function(dt)
		frame += 1
		if Animator.Reduced and frame % 2 == 0 then
			return
		end
		local t = os.clock()
		local camPos = camera.CFrame.Position
		for model, data in pairs(creatures) do
			if model.Parent and model.PrimaryPart then
				if (data.Base.Position - camPos).Magnitude < LOD_DISTANCE then
					local offset, squash = creatureOffset(data, t)
					model:PivotTo(data.Base * offset)
					if squash ~= 1 and model.PrimaryPart then
						-- lieve schiacciamento del corpo nel salto
						local s = model.PrimaryPart:GetAttribute("BaseSize")
						if not s then
							model.PrimaryPart:SetAttribute("BaseSize", model.PrimaryPart.Size)
							s = model.PrimaryPart.Size
						end
						model.PrimaryPart.Size = Vector3.new(s.X * (2 - squash), s.Y * squash, s.Z * (2 - squash))
					end
				end
			else
				creatures[model] = nil
			end
		end
		for part, data in pairs(spinners) do
			if part.Parent then
				if (data.Base.Position - camPos).Magnitude < LOD_DISTANCE then
					if data.Kind == "spin" then
						part.CFrame = data.Base * CFrame.Angles(0, 0, t * 2.5)
						for _, c in ipairs(data.Children) do
							c.Part.CFrame = part.CFrame * c.Offset
						end
					elseif data.Kind == "spinZ" then
						part.CFrame = data.Base * CFrame.Angles(t * 0.6, 0, 0)
					elseif data.Kind == "sway" then
						part.CFrame = data.Base * CFrame.Angles(0, 0, math.sin(t * 1.5 + data.Phase) * 0.12)
					elseif data.Kind == "bob" then
						part.CFrame = data.Base * CFrame.new(0, math.sin(t * 2 + data.Phase) * 0.2, 0) * CFrame.Angles(0, t * 0.8, 0)
					elseif data.Kind == "pulse" then
						local s = 1 + math.sin(t * 2) * 0.08
						part.Size = Vector3.new(3 * s, 3 * s, 3 * s)
					end
				end
			else
				spinners[part] = nil
			end
		end
		for model, data in pairs(sentinels) do
			if model.Parent and data.Cone.Parent then
				if (data.Base - camPos).Magnitude < LOD_DISTANCE then
					ModuleModel.OrientSentinel(model, data.Offset + t * data.Speed * 0.5)
				end
			else
				sentinels[model] = nil
			end
		end
		for part, data in pairs(platforms) do
			if part.Parent and data.Root.Parent then
				if (data.Root.Position - camPos).Magnitude < LOD_DISTANCE then
					local phase = (t / data.Period + data.Phase) * math.pi * 2
					part.CFrame = data.Root.CFrame * CFrame.new(0, 0.1, math.sin(phase) * data.Travel / 2)
				end
			else
				platforms[part] = nil
			end
		end
	end)
end

return Animator
