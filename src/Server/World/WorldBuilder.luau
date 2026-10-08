--!nonstrict
--[[
	WorldBuilder: costruisce l'isola hub (piazza, Albero delle Nuvole, portale delle incursioni,
	bacheca delle commissioni, galleria dei vivai, bottega dello stile, vivaio dimostrativo),
	gli slot dei plot e delle arene, e configura illuminazione/atmosfera.
	Tutto procedurale: nessun asset esterno richiesto.
]]
local Lighting = game:GetService("Lighting")
local Workspace = game:GetService("Workspace")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local PartUtil = require(Shared.Models.PartUtil)
local PlotBuilder = require(Shared.Models.PlotBuilder)
local Simulated = require(Shared.Catalog.SimulatedVivai)

local WorldBuilder = {}

local HUB_RADIUS = 92

function WorldBuilder.SetupLighting()
	for _, c in ipairs(Lighting:GetChildren()) do
		c:Destroy()
	end
	local sky = Instance.new("Sky")
	sky.Name = "Sky"
	sky.SunAngularSize = 14
	sky.MoonAngularSize = 8
	sky.StarCount = 1500
	sky.Parent = Lighting

	local atm = Instance.new("Atmosphere")
	atm.Density = 0.32
	atm.Offset = 0.6
	atm.Color = Color3.fromRGB(205, 220, 245)
	atm.Decay = Color3.fromRGB(150, 170, 210)
	atm.Glare = 0.35
	atm.Haze = 1.4
	atm.Parent = Lighting

	local bloom = Instance.new("BloomEffect")
	bloom.Intensity = 0.6
	bloom.Size = 32
	bloom.Threshold = 1.1
	bloom.Parent = Lighting

	local rays = Instance.new("SunRaysEffect")
	rays.Intensity = 0.08
	rays.Spread = 0.6
	rays.Parent = Lighting

	local cc = Instance.new("ColorCorrectionEffect")
	cc.Name = "ThemeCorrection"
	cc.Saturation = 0.12
	cc.Contrast = 0.05
	cc.TintColor = Color3.new(1, 1, 1)
	cc.Parent = Lighting

	local clouds = Workspace.Terrain:FindFirstChildOfClass("Clouds") or Instance.new("Clouds")
	clouds.Cover = 0.72
	clouds.Density = 0.42
	clouds.Color = Color3.fromRGB(250, 252, 255)
	clouds.Parent = Workspace.Terrain
end

local function station(parent, cf, name, promptText, stationId, color)
	local m = PartUtil.Model(name, parent)
	m:SetAttribute("Station", stationId)
	local base = PartUtil.Cylinder(4.5, 0.6, color, cf * CFrame.new(0, 0.3, 0), m, { Material = Enum.Material.Marble, Name = "Base" })
	local prompt = PartUtil.Prompt(base, promptText, "", 0, 14)
	prompt.Name = "StationPrompt"
	prompt:SetAttribute("Station", stationId)
	PartUtil.Billboard(base, { Size = UDim2.fromOffset(240, 44), Offset = Vector3.new(0, 11, 0), Text = promptText, TextColor = color, MaxDistance = 140 })
	return m, base
end

local function buildTree(parent, cf)
	local m = PartUtil.Model("AlberoDelleNuvole", parent)
	PartUtil.Cylinder(2.6, 18, Color3.fromRGB(130, 100, 80), cf * CFrame.new(0, 9, 0), m, { Material = Enum.Material.Wood, Name = "Trunk" })
	PartUtil.Cylinder(4.2, 1.2, Color3.fromRGB(120, 90, 70), cf * CFrame.new(0, 0.6, 0), m, { Material = Enum.Material.Wood, Name = "Roots" })
	local rng = Random.new(7)
	for i = 1, 4 do
		local a = i * 1.6
		PartUtil.Part({ Size = Vector3.new(1.4, 7, 1.4), Color = Color3.fromRGB(130, 100, 80), Material = Enum.Material.Wood, CFrame = cf * CFrame.new(math.cos(a) * 3, 17, math.sin(a) * 3) * CFrame.Angles(math.sin(a) * 0.6, 0, math.cos(a) * 0.6), Parent = m, Name = "Branch", CanCollide = false })
	end
	for i = 1, 9 do
		local a = i * 0.7
		local r = 4 + (i % 3) * 2.5
		local y = 20 + rng:NextNumber(-1.5, 3)
		PartUtil.Cloud(cf * CFrame.new(math.cos(a) * r, y, math.sin(a) * r), rng:NextNumber(3.5, 5.5), m, Color3.fromRGB(252, 253, 255), 0)
	end
	local core = PartUtil.Ball(3, Color3.fromRGB(255, 215, 110), cf * CFrame.new(0, 22, 0), m, { Material = Enum.Material.Neon, Name = "Core" })
	PartUtil.Light(core, Color3.fromRGB(255, 215, 110), 2.5, 40)
	PartUtil.Emitter(core, { Color = Color3.fromRGB(255, 230, 150), Rate = 12, Speed = NumberRange.new(2, 5), Lifetime = NumberRange.new(1.5, 3), Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.6), NumberSequenceKeypoint.new(1, 0) }), Acceleration = Vector3.new(0, -2, 0), Name = "Sparks" })
	core:SetAttribute("Anim", "pulse")
end

local function buildRaidPortal(parent, cf)
	local m = station(parent, cf, "PortaleIncursioni", Strings.PromptRaidPortal, "raid", Color3.fromRGB(255, 170, 220))
	local ring = PartUtil.Part({ Shape = Enum.PartType.Cylinder, Size = Vector3.new(1.2, 14, 14), Color = Color3.fromRGB(250, 250, 255), Material = Enum.Material.Marble, CFrame = cf * CFrame.new(0, 7.6, 0) * CFrame.Angles(0, 0, 0), Parent = m, Name = "Ring", CanCollide = false })
	ring.CFrame = cf * CFrame.new(0, 7.6, 0) * CFrame.Angles(0, math.rad(90), 0)
	local inner = PartUtil.Part({ Shape = Enum.PartType.Cylinder, Size = Vector3.new(0.4, 12, 12), Color = Color3.fromRGB(255, 170, 220), Material = Enum.Material.ForceField, Transparency = 0.2, CFrame = cf * CFrame.new(0, 7.6, 0) * CFrame.Angles(0, math.rad(90), 0), Parent = m, Name = "Swirl", CanCollide = false, CanQuery = false })
	inner:SetAttribute("Anim", "spinZ")
	PartUtil.Light(inner, Color3.fromRGB(255, 170, 220), 2, 30)
	PartUtil.Emitter(inner, { Color = Color3.fromRGB(255, 200, 240), Rate = 20, Speed = NumberRange.new(1, 3), Lifetime = NumberRange.new(1, 2), Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.4), NumberSequenceKeypoint.new(1, 0) }), Name = "Motes" })
	for _, dx in ipairs({ -7.5, 7.5 }) do
		PartUtil.Part({ Size = Vector3.new(1.6, 3, 1.6), Color = Color3.fromRGB(230, 232, 245), Material = Enum.Material.Marble, CFrame = cf * CFrame.new(dx, 1.5, 0), Parent = m, Name = "Pillar" })
	end
end

local function buildBoard(parent, cf)
	local m = station(parent, cf, "Bacheca", Strings.PromptBoard, "board", Color3.fromRGB(255, 200, 110))
	for _, dx in ipairs({ -4, 4 }) do
		PartUtil.Part({ Size = Vector3.new(0.6, 8, 0.6), Color = Color3.fromRGB(130, 100, 80), Material = Enum.Material.Wood, CFrame = cf * CFrame.new(dx, 4, 0), Parent = m, Name = "Post" })
	end
	local board = PartUtil.Part({ Size = Vector3.new(9, 5.5, 0.5), Color = Color3.fromRGB(200, 160, 120), Material = Enum.Material.WoodPlanks, CFrame = cf * CFrame.new(0, 5.5, 0), Parent = m, Name = "Board" })
	PartUtil.Part({ Size = Vector3.new(10, 0.8, 2), Color = Color3.fromRGB(230, 120, 110), Material = Enum.Material.SmoothPlastic, CFrame = cf * CFrame.new(0, 8.6, 0), Parent = m, Name = "Roof" })
	local sg = Instance.new("SurfaceGui")
	sg.Face = Enum.NormalId.Front
	sg.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
	sg.PixelsPerStud = 40
	sg.Parent = board
	local title = Instance.new("TextLabel")
	title.Size = UDim2.new(1, 0, 0.22, 0)
	title.BackgroundTransparency = 1
	title.Font = Enum.Font.FredokaOne
	title.TextScaled = true
	title.TextColor3 = Color3.fromRGB(60, 40, 30)
	title.Text = "Commissioni del giorno"
	title.Parent = sg
	for i = 1, 3 do
		local note = Instance.new("TextLabel")
		note.Name = "Note" .. i
		note.Size = UDim2.new(0.3, 0, 0.6, 0)
		note.Position = UDim2.new(0.03 + (i - 1) * 0.32, 0, 0.3, 0)
		note.BackgroundColor3 = ({ Color3.fromRGB(255, 240, 170), Color3.fromRGB(200, 240, 255), Color3.fromRGB(255, 210, 230) })[i]
		note.Font = Enum.Font.GothamMedium
		note.TextWrapped = true
		note.TextScaled = true
		note.TextColor3 = Color3.fromRGB(50, 50, 70)
		note.Text = "Interagisci per vedere le tue commissioni"
		note.Rotation = (i - 2) * 3
		note.Parent = sg
		local corner = Instance.new("UICorner")
		corner.CornerRadius = UDim.new(0, 6)
		corner.Parent = note
	end
end

local function buildGallery(parent, cf)
	local m = station(parent, cf, "Galleria", Strings.PromptGallery, "gallery", Color3.fromRGB(160, 200, 255))
	for i = -1, 1 do
		local x = i * 7
		for _, dx in ipairs({ -2.6, 2.6 }) do
			PartUtil.Part({ Size = Vector3.new(0.8, 7, 0.8), Color = Color3.fromRGB(240, 242, 252), Material = Enum.Material.Marble, CFrame = cf * CFrame.new(x + dx, 3.5, -3), Parent = m, Name = "Column" })
		end
		PartUtil.Part({ Size = Vector3.new(6, 0.8, 0.8), Color = Color3.fromRGB(240, 242, 252), Material = Enum.Material.Marble, CFrame = cf * CFrame.new(x, 7.2, -3), Parent = m, Name = "Lintel" })
		local frame = PartUtil.Part({ Size = Vector3.new(4.4, 4.4, 0.3), Color = ({ Color3.fromRGB(255, 190, 70), Color3.fromRGB(96, 160, 240), Color3.fromRGB(196, 130, 255) })[i + 2], Material = Enum.Material.Neon, Transparency = 0.35, CFrame = cf * CFrame.new(x, 4, -3), Parent = m, Name = "Frame", CanCollide = false })
		PartUtil.Light(frame, frame.Color, 0.8, 12)
	end
end

local function buildShop(parent, cf)
	local m = station(parent, cf, "Bottega", Strings.PromptShop, "shop", Color3.fromRGB(226, 142, 255))
	PartUtil.Part({ Size = Vector3.new(8, 2.4, 3), Color = Color3.fromRGB(200, 160, 120), Material = Enum.Material.WoodPlanks, CFrame = cf * CFrame.new(0, 1.2, -2), Parent = m, Name = "Counter" })
	for _, dx in ipairs({ -3.6, 3.6 }) do
		PartUtil.Part({ Size = Vector3.new(0.5, 7, 0.5), Color = Color3.fromRGB(130, 100, 80), Material = Enum.Material.Wood, CFrame = cf * CFrame.new(dx, 3.5, -3.5), Parent = m, Name = "Post" })
	end
	for i = 0, 3 do
		local col = (i % 2 == 0) and Color3.fromRGB(226, 142, 255) or Color3.fromRGB(250, 250, 255)
		PartUtil.Part({ Size = Vector3.new(2.2, 0.3, 4.5), Color = col, Material = Enum.Material.Fabric, CFrame = cf * CFrame.new(-3.3 + i * 2.2, 7, -2) * CFrame.Angles(math.rad(-12), 0, 0), Parent = m, Name = "Awning", CanCollide = false })
	end
	for i = 1, 3 do
		local gem = PartUtil.Part({ Size = Vector3.new(0.9, 1.3, 0.9), Color = ({ Color3.fromRGB(255, 200, 90), Color3.fromRGB(150, 210, 255), Color3.fromRGB(255, 160, 220) })[i], Material = Enum.Material.Glass, Transparency = 0.15, Reflectance = 0.3, CFrame = cf * CFrame.new(-2.5 + i * 1.6, 3.1, -2) * CFrame.Angles(0, math.rad(45), 0), Parent = m, Name = "Gem", CanCollide = false })
		gem:SetAttribute("Anim", "bob")
	end
end

local function buildHubIsland(parent)
	local m = PartUtil.Model("Hub", parent)
	local origin = CFrame.new(0, 0, 0)
	PartUtil.Cylinder(HUB_RADIUS, 2, Color3.fromRGB(128, 200, 120), origin * CFrame.new(0, -1, 0), m, { Material = Enum.Material.Grass, Name = "Ground" })
	PartUtil.Cylinder(HUB_RADIUS + 2, 1.2, Color3.fromRGB(240, 246, 255), origin * CFrame.new(0, -1.8, 0), m, { Material = Enum.Material.SmoothPlastic, Name = "Rim" })
	-- piazza centrale in pietra
	PartUtil.Cylinder(22, 0.4, Color3.fromRGB(226, 222, 212), origin * CFrame.new(0, 0.2, 0), m, { Material = Enum.Material.Marble, Name = "Plaza" })
	PartUtil.Cylinder(23, 0.3, Color3.fromRGB(255, 215, 110), origin * CFrame.new(0, 0.1, 0), m, { Material = Enum.Material.Neon, Transparency = 0.5, Name = "PlazaRing", CanCollide = false })
	-- sentieri verso le stazioni
	for _, a in ipairs({ 0, 90, 180, 270 }) do
		local rad = math.rad(a)
		PartUtil.Part({ Size = Vector3.new(6, 0.3, 40), Color = Color3.fromRGB(226, 222, 212), Material = Enum.Material.Marble, CFrame = origin * CFrame.Angles(0, rad, 0) * CFrame.new(0, 0.15, -42), Parent = m, Name = "Path" })
	end
	-- roccia e nuvole sotto
	PartUtil.Part({ Size = Vector3.new(HUB_RADIUS * 1.5, 14, HUB_RADIUS * 1.5), Material = Enum.Material.Slate, Color = Color3.fromRGB(150, 160, 190), CFrame = origin * CFrame.new(0, -9, 0) * CFrame.Angles(0, math.rad(15), 0), Parent = m, Name = "Rock", CanCollide = false })
	PartUtil.Part({ Size = Vector3.new(HUB_RADIUS * 0.9, 16, HUB_RADIUS * 0.9), Material = Enum.Material.Slate, Color = Color3.fromRGB(130, 140, 175), CFrame = origin * CFrame.new(0, -22, 0) * CFrame.Angles(0, math.rad(40), 0), Parent = m, Name = "Rock2", CanCollide = false })
	PartUtil.Part({ Size = Vector3.new(HUB_RADIUS * 0.4, 18, HUB_RADIUS * 0.4), Material = Enum.Material.Slate, Color = Color3.fromRGB(115, 125, 160), CFrame = origin * CFrame.new(0, -38, 0) * CFrame.Angles(0, math.rad(70), 0), Parent = m, Name = "Rock3", CanCollide = false })
	local rng = Random.new(42)
	for i = 1, 18 do
		local a = (i / 18) * math.pi * 2 + rng:NextNumber(-0.2, 0.2)
		local r = HUB_RADIUS * rng:NextNumber(0.9, 1.08)
		PartUtil.Cloud(origin * CFrame.new(math.cos(a) * r, -4 + rng:NextNumber(-3, 1), math.sin(a) * r), rng:NextNumber(5, 8), m, Color3.fromRGB(250, 252, 255), 0.02)
	end
	-- spawn
	local spawn = Instance.new("SpawnLocation")
	spawn.Name = "HubSpawn"
	spawn.Size = Vector3.new(10, 1, 10)
	spawn.CFrame = origin * CFrame.new(0, 0.5, 26)
	spawn.Anchored = true
	spawn.Transparency = 1
	spawn.CanCollide = false
	spawn.Neutral = true
	spawn.Duration = 0
	spawn.Parent = m

	buildTree(m, origin * CFrame.new(0, 0, 0))
	buildRaidPortal(m, origin * CFrame.new(0, 0, -68) * CFrame.Angles(0, 0, 0))
	buildBoard(m, origin * CFrame.new(68, 0, 0) * CFrame.Angles(0, math.rad(90), 0))
	buildGallery(m, origin * CFrame.new(0, 0, 68) * CFrame.Angles(0, math.rad(180), 0))
	buildShop(m, origin * CFrame.new(-68, 0, 0) * CFrame.Angles(0, math.rad(-90), 0))

	-- stazione "torna al tuo vivaio" vicino allo spawn
	local homeStation = station(m, origin * CFrame.new(0, 0, 36), "RitornoVivaio", Strings.PromptHome, "home", Color3.fromRGB(150, 232, 200))
	local ring = PartUtil.Part({ Size = Vector3.new(7, 7, 0.4), Color = Color3.fromRGB(150, 232, 200), Material = Enum.Material.ForceField, Transparency = 0.3, CFrame = origin * CFrame.new(0, 4, 36), Parent = homeStation, Name = "HomeRing", CanCollide = false, CanQuery = false })
	PartUtil.Light(ring, Color3.fromRGB(150, 232, 200), 1.2, 16)

	-- decorazioni sparse: lanterne e cespugli lungo il bordo della piazza
	for i = 1, 12 do
		local a = (i / 12) * math.pi * 2 + math.rad(15)
		local cf = origin * CFrame.new(math.cos(a) * 30, 0, math.sin(a) * 30)
		if i % 2 == 0 then
			local post = PartUtil.Part({ Size = Vector3.new(0.4, 5, 0.4), Color = Color3.fromRGB(120, 90, 60), Material = Enum.Material.Wood, CFrame = cf * CFrame.new(0, 2.5, 0), Parent = m, Name = "LampPost" })
			local lamp = PartUtil.Ball(1.2, Color3.fromRGB(255, 225, 150), cf * CFrame.new(0, 5.4, 0), m, { Material = Enum.Material.Neon, Name = "Lamp" })
			PartUtil.Light(lamp, Color3.fromRGB(255, 225, 150), 1, 14)
		else
			PartUtil.Ball(2.4, Color3.fromRGB(110, 190, 150), cf * CFrame.new(0, 1, 0), m, { Material = Enum.Material.Grass, Name = "Bush" })
			PartUtil.Ball(1.6, Color3.fromRGB(130, 205, 160), cf * CFrame.new(0.9, 1.4, 0.5), m, { Material = Enum.Material.Grass, Name = "Bush" })
		end
	end
	return m
end

local function buildDemoIsland(parent)
	-- isolotto a nord-est collegato da un ponte, con il vivaio dimostrativo
	local origin = CFrame.new(120, 0, -120)
	local m = PartUtil.Model("IsolaDemo", parent)
	-- ponte di nuvola
	local from = Vector3.new(HUB_RADIUS * math.cos(math.rad(-45)), 0, HUB_RADIUS * math.sin(math.rad(-45)))
	local to = origin.Position + Vector3.new(-32, 0, 0)
	local mid = (from + to) / 2
	local len = (to - from).Magnitude
	local bridge = PartUtil.Part({ Size = Vector3.new(6, 1, len + 6), Color = Color3.fromRGB(245, 248, 255), Material = Enum.Material.SmoothPlastic, CFrame = CFrame.lookAt(mid, to) * CFrame.new(0, -0.5, 0), Parent = m, Name = "Bridge" })
	for i = 0, math.floor(len / 8) do
		local p = from + (to - from).Unit * (i * 8)
		PartUtil.Cloud(CFrame.new(p.X, -2.5, p.Z), 3.4, m, Color3.fromRGB(250, 252, 255), 0.02)
	end
	for _, side in ipairs({ -3.2, 3.2 }) do
		PartUtil.Part({ Size = Vector3.new(0.5, 1.4, len + 6), Color = Color3.fromRGB(160, 200, 255), Material = Enum.Material.Neon, Transparency = 0.4, CFrame = CFrame.lookAt(mid, to) * CFrame.new(side, 0.4, 0), Parent = m, Name = "Rail", CanCollide = false })
	end
	local demo = Simulated.ByKey.sim_faro
	local creatures = {}
	for i, c in ipairs(demo.Creatures) do
		table.insert(creatures, { Uid = "demo" .. i, Id = c.Id, Variant = "base", x = c.x, z = c.z, Buffer = 0 })
	end
	local plot = PlotBuilder.Build(m, origin, {
		Creatures = creatures,
		Layout = demo.Layout,
		Decorations = { { Id = "lanterna_nube", x = 1, z = 1, Rot = 0 }, { Id = "fontanella", x = 10, z = 1, Rot = 0 }, { Id = "girandola", x = 1, z = 10, Rot = 0 }, { Id = "arco_luce", x = 10, z = 10, Rot = 0 } },
		Skin = "skin_cristallo",
		OwnerName = "Vivaio dimostrativo",
		Exposed = demo.Exposed,
		Vault = 820,
		VaultCap = 1200,
	}, "demo")
	plot.Model.Name = "VivaioDemo"
	plot.Model:SetAttribute("Station", "demo")
	local prompt = PartUtil.Prompt(plot.PozzaBasin, Strings.PromptDemo, "Osserva", 0, 16)
	prompt.Name = "StationPrompt"
	prompt:SetAttribute("Station", "demo")
	return m
end

local function buildScenery(parent)
	local m = PartUtil.Model("Scenario", parent)
	local rng = Random.new(2026)
	for i = 1, 40 do
		local a = rng:NextNumber(0, math.pi * 2)
		local r = rng:NextNumber(140, 520)
		local y = rng:NextNumber(-60, 70)
		local p = Vector3.new(math.cos(a) * r, y, math.sin(a) * r)
		if (p - Vector3.new(0, 0, 0)).Magnitude > 120 then
			PartUtil.Cloud(CFrame.new(p), rng:NextNumber(5, 12), m, Color3.fromRGB(250, 252, 255), rng:NextNumber(0.05, 0.3))
			if rng:NextNumber() < 0.3 then
				PartUtil.Part({ Size = Vector3.new(rng:NextNumber(6, 14), rng:NextNumber(4, 10), rng:NextNumber(6, 14)), Material = Enum.Material.Slate, Color = Color3.fromRGB(140, 150, 185), CFrame = CFrame.new(p + Vector3.new(0, -6, 0)) * CFrame.Angles(rng:NextNumber(-0.3, 0.3), rng:NextNumber(0, 3), rng:NextNumber(-0.3, 0.3)), Parent = m, Name = "FloatingRock", CanCollide = false })
			end
		end
	end
end

function WorldBuilder.Build()
	local world = Workspace:FindFirstChild("World") or Instance.new("Folder")
	world.Name = "World"
	world.Parent = Workspace

	WorldBuilder.SetupLighting()
	buildHubIsland(world)
	buildDemoIsland(world)
	buildScenery(world)

	local plots = Instance.new("Folder")
	plots.Name = "Plots"
	plots.Parent = Workspace
	local arenas = Instance.new("Folder")
	arenas.Name = "Arenas"
	arenas.Parent = Workspace
	return world
end

function WorldBuilder.PlotOrigin(index)
	local a = (index - 1) / Config.Plots.Count * math.pi * 2
	local r = Config.Plots.RingRadius
	local pos = Vector3.new(math.cos(a) * r, Config.Plots.Height, math.sin(a) * r)
	-- il fronte (ingresso, -Z locale) guarda verso l'hub
	return CFrame.lookAt(pos, Vector3.new(0, Config.Plots.Height, 0)) * CFrame.Angles(0, math.pi, 0)
end

function WorldBuilder.ArenaOrigin(index)
	local o = Config.Arenas.Origin
	return CFrame.new(o.X + (index - 1) * Config.Arenas.Spacing, o.Y, o.Z)
end

function WorldBuilder.HubSpawnCFrame()
	return CFrame.new(0, 4, 26)
end

return WorldBuilder
