--!nonstrict
local Decorations = require(script.Parent.Parent.Catalog.Decorations)
local PartUtil = require(script.Parent.PartUtil)

local DecorationModel = {}

local kinds = {}

kinds.lantern = function(m, v)
	PartUtil.Part({ Size = Vector3.new(0.35, 4.5, 0.35), Color = v.Accent, Material = Enum.Material.Wood, CFrame = CFrame.new(0, 2.25, 0), Parent = m, Name = "Post" })
	PartUtil.Part({ Size = Vector3.new(1.6, 0.25, 0.35), Color = v.Accent, Material = Enum.Material.Wood, CFrame = CFrame.new(0.6, 4.4, 0), Parent = m, Name = "Arm" })
	local lamp = PartUtil.Part({ Size = Vector3.new(0.9, 1.1, 0.9), Color = v.Color, Material = Enum.Material.Neon, Transparency = 0.1, CFrame = CFrame.new(1.2, 3.7, 0), Parent = m, Name = "Lamp", CanCollide = false })
	lamp:SetAttribute("Anim", "sway")
	PartUtil.Light(lamp, v.Color, 1.2, 12)
end

kinds.bush = function(m, v)
	for i, o in ipairs({ { 0, 0.9, 0, 2.2 }, { 0.8, 0.7, 0.4, 1.6 }, { -0.7, 0.75, -0.3, 1.7 }, { 0.1, 1.5, -0.5, 1.3 } }) do
		PartUtil.Ball(o[4], v.Color, CFrame.new(o[1], o[2], o[3]), m, { Material = Enum.Material.Grass, Name = "Leaf", CanCollide = false })
	end
	for i = 1, 6 do
		local a = i * 1.05
		PartUtil.Ball(0.3, v.Accent or Color3.new(1, 1, 1), CFrame.new(math.cos(a) * 1.1, 1.1 + math.sin(a * 2) * 0.5, math.sin(a) * 1.1), m, { Material = Enum.Material.Neon, Name = "Star", CastShadow = false })
	end
end

kinds.sundial = function(m, v)
	PartUtil.Cylinder(1.6, 0.5, v.Color, CFrame.new(0, 0.25, 0), m, { Material = Enum.Material.Marble, Name = "Disc" })
	local gnomon = PartUtil.Part({ Class = "WedgePart", Size = Vector3.new(0.3, 1.6, 1.6), Color = v.Accent, Material = Enum.Material.Neon, CFrame = CFrame.new(0, 1.3, -0.3), Parent = m, Name = "Gnomon", CanCollide = false })
	PartUtil.Light(gnomon, v.Accent, 0.6, 8)
end

kinds.fountain = function(m, v)
	PartUtil.Cylinder(1.8, 0.9, v.Color, CFrame.new(0, 0.45, 0), m, { Material = Enum.Material.Marble, Name = "Basin" })
	local water = PartUtil.Cylinder(1.5, 0.3, v.Accent, CFrame.new(0, 0.95, 0), m, { Material = Enum.Material.Neon, Transparency = 0.3, Name = "Water", CanCollide = false })
	PartUtil.Cylinder(0.35, 1.6, v.Color, CFrame.new(0, 1.6, 0), m, { Material = Enum.Material.Marble, Name = "Spout", CanCollide = false })
	PartUtil.Emitter(water, { Color = v.Accent, Rate = 14, Speed = NumberRange.new(6, 9), Lifetime = NumberRange.new(0.8, 1.2), Acceleration = Vector3.new(0, -14, 0), Spread = Vector2.new(12, 12), Size = NumberSequence.new(0.2), Name = "Jet" })
	PartUtil.Light(water, v.Accent, 0.8, 9)
end

kinds.pinwheel = function(m, v)
	PartUtil.Part({ Size = Vector3.new(0.25, 3.5, 0.25), Color = Color3.fromRGB(230, 230, 240), CFrame = CFrame.new(0, 1.75, 0), Parent = m, Name = "Post" })
	local hub = PartUtil.Ball(0.5, v.Accent or Color3.new(1, 1, 1), CFrame.new(0, 3.6, -0.3), m, { Material = Enum.Material.Neon, Name = "Hub" })
	hub:SetAttribute("Anim", "spin")
	for i = 1, 4 do
		local a = (i / 4) * math.pi * 2
		local blade = PartUtil.Part({ Class = "WedgePart", Size = Vector3.new(0.12, 1.1, 1.1), Color = (i % 2 == 0) and v.Color or (v.Accent or v.Color), Material = Enum.Material.SmoothPlastic, CFrame = CFrame.new(0, 3.6, -0.3) * CFrame.Angles(0, 0, a) * CFrame.new(0, 0.75, 0) * CFrame.Angles(math.rad(90), 0, 0), Parent = m, Name = "Blade", CanCollide = false })
		blade:SetAttribute("SpinChild", true)
	end
end

kinds.arch = function(m, v)
	local segs = 9
	for i = 1, segs do
		local t = (i - 1) / (segs - 1)
		local a = math.rad(180 - t * 180)
		local c = v.Color:Lerp(v.Accent or v.Color, t)
		PartUtil.Part({ Size = Vector3.new(0.5, 0.9, 0.5), Color = c, Material = Enum.Material.Neon, Transparency = 0.1, CFrame = CFrame.new(math.cos(a) * 2.2, 0.4 + math.sin(a) * 3.2, 0) * CFrame.Angles(0, 0, a + math.rad(90)), Parent = m, Name = "Seg", CanCollide = false, CastShadow = false })
	end
end

kinds.throne = function(m, v)
	PartUtil.Cloud(CFrame.new(0, 0.9, 0), 1.3, m, v.Color, 0)
	PartUtil.Part({ Size = Vector3.new(2.6, 0.6, 2.4), Color = v.Color, CFrame = CFrame.new(0, 1.7, 0), Parent = m, Name = "Seat" })
	PartUtil.Part({ Size = Vector3.new(2.6, 3, 0.5), Color = v.Color, CFrame = CFrame.new(0, 3.2, 1.0), Parent = m, Name = "Back" })
	local crown = PartUtil.Part({ Size = Vector3.new(1.4, 0.6, 0.4), Color = v.Accent, Material = Enum.Material.Neon, CFrame = CFrame.new(0, 5.0, 1.0), Parent = m, Name = "Crown", CanCollide = false })
	PartUtil.Light(crown, v.Accent, 1, 10)
end

kinds.bench = function(m, v)
	PartUtil.Part({ Size = Vector3.new(3.2, 0.4, 1.2), Color = v.Color, CFrame = CFrame.new(0, 1.2, 0), Parent = m, Name = "Seat" })
	PartUtil.Part({ Size = Vector3.new(3.2, 1.2, 0.3), Color = v.Color, CFrame = CFrame.new(0, 2.0, 0.5), Parent = m, Name = "Back" })
	for _, dx in ipairs({ -1.3, 1.3 }) do
		PartUtil.Part({ Size = Vector3.new(0.3, 1.0, 1.0), Color = v.Accent, Material = Enum.Material.Metal, CFrame = CFrame.new(dx, 0.5, 0), Parent = m, Name = "Leg" })
	end
end

function DecorationModel.Build(decoId, parent, ghost)
	local def = Decorations.ById[decoId]
	if not def then
		return nil
	end
	local m = PartUtil.Model("Deco_" .. decoId, nil)
	m:SetAttribute("DecorationId", decoId)
	local r = PartUtil.Part({ Size = Vector3.new(4, 0.2, 4), Transparency = 1, CanCollide = false, CanQuery = false, CFrame = CFrame.new(), Parent = m, Name = "Root" })
	m.PrimaryPart = r
	local builder = kinds[def.Visual.Kind]
	if builder then
		builder(m, def.Visual)
	end
	if ghost then
		for _, d in ipairs(m:GetDescendants()) do
			if d:IsA("BasePart") then
				d.CanCollide = false
				d.Transparency = math.max(d.Transparency, 0.5)
			elseif d:IsA("ParticleEmitter") or d:IsA("PointLight") then
				d.Enabled = false
			end
		end
	end
	if parent then
		m.Parent = parent
	end
	return m
end

return DecorationModel
