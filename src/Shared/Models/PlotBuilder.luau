--!nonstrict
--[[
	PlotBuilder: costruisce un vivaio completo (piattaforma, pozza, cassaforte, creature,
	moduli di difesa, decorazioni, ingresso/uscita) a partire da una "vista" dei dati.
	Usato per i plot dei giocatori, le arene di incursione (copia istanziata del layout),
	le visite e il vivaio dimostrativo dell'hub.

	view = {
		Creatures = { {Uid, Id, Variant, x, z, Buffer} }, Layout = {Modules}, Decorations = { {Id,x,z,Rot} },
		Skin = cosmeticId, OwnerName = string?, Nameplate = cosmeticId?, Exposed = n, Vault = n, VaultCap = n,
	}
	mode = "home" | "raid" | "visit" | "demo"
]]
local Config = require(script.Parent.Parent.Config)
local Cosmetics = require(script.Parent.Parent.Catalog.Cosmetics)
local Creatures = require(script.Parent.Parent.Catalog.Creatures)
local Defenses = require(script.Parent.Parent.Catalog.Defenses)
local GridUtil = require(script.Parent.Parent.Util.GridUtil)
local Format = require(script.Parent.Parent.Util.Format)
local Strings = require(script.Parent.Parent.Strings)
local PartUtil = require(script.Parent.PartUtil)
local MeshUtil = require(script.Parent.MeshUtil)
local CreatureModel = require(script.Parent.CreatureModel)
local ModuleModel = require(script.Parent.ModuleModel)
local DecorationModel = require(script.Parent.DecorationModel)

local G = Config.Grid
local CELL = G.CellSize
local HALF = G.Size * CELL / 2 -- 24
local MARGIN = (Config.Plots.PlatformSize - G.Size * CELL) / 2 -- 8

local PlotBuilder = {}
PlotBuilder.__index = PlotBuilder

local GAP_MODULES = { piattaforma = true, arcobaleno = true }

local function skinData(skinId)
	local c = Cosmetics.Get(skinId or "skin_prato") or Cosmetics.Get("skin_prato")
	return c.Data
end

local function materialFromName(name)
	local ok, mat = pcall(function()
		return Enum.Material[name]
	end)
	return ok and mat or Enum.Material.Grass
end

-- ───────────────────────── costruzione base ─────────────────────────

function PlotBuilder.Build(parent, origin: CFrame, view, mode)
	local self = setmetatable({}, PlotBuilder)
	self.Origin = origin
	self.Mode = mode or "home"
	self.View = view
	self.Model = PartUtil.Model("Vivaio", nil)
	self.Model:SetAttribute("Mode", self.Mode)
	self.Model:SetAttribute("Origin", origin)
	self.Folders = {}
	for _, name in ipairs({ "Tiles", "Creatures", "Modules", "Decorations", "Structure" }) do
		local f = Instance.new("Folder")
		f.Name = name
		f.Parent = self.Model
		self.Folders[name] = f
	end
	self.CreatureModels = {} -- uid -> model
	self.Tiles = {} -- key -> tile part

	self:_buildBase()
	self:_buildStructures()
	self:RebuildModules(view.Layout)
	for _, c in ipairs(view.Creatures or {}) do
		self:AddCreature(c)
	end
	for i, d in ipairs(view.Decorations or {}) do
		self:AddDecoration(d, i)
	end
	self:SetExposed(view.Exposed or 0)
	self:SetVault(view.Vault or 0, view.VaultCap or Config.Vault.Capacities[1])
	self.Model.Parent = parent
	return self
end

function PlotBuilder:_buildBase()
	local skin = skinData(self.View.Skin)
	local mat = materialFromName(skin.Material)
	local structure = self.Folders.Structure
	local origin = self.Origin
	local size = Config.Plots.PlatformSize

	-- piastrelle della griglia (scacchiera leggera)
	for x = 0, G.Size - 1 do
		for z = 0, G.Size - 1 do
			local shade = ((x + z) % 2 == 0) and 1 or 0.92
			local tile = PartUtil.Part({
				Size = Vector3.new(CELL, 1, CELL), Material = mat,
				Color = Color3.new(skin.Color.R * shade, skin.Color.G * shade, skin.Color.B * shade),
				CFrame = origin * CFrame.new(GridUtil.CellToLocal(x, z, -0.5)), Parent = self.Folders.Tiles, Name = "Tile",
			})
			tile:SetAttribute("x", x)
			tile:SetAttribute("z", z)
			self.Tiles[GridUtil.Key(x, z)] = tile
		end
	end
	-- cornice esterna (margine) con colore trim
	local trim = skin.Trim or Color3.new(1, 1, 1)
	local half = size / 2
	for _, side in ipairs({
		{ CFrame.new(0, -0.6, -(HALF + MARGIN / 2)), Vector3.new(size, 1.2, MARGIN) },
		{ CFrame.new(0, -0.6, HALF + MARGIN / 2), Vector3.new(size, 1.2, MARGIN) },
		{ CFrame.new(-(HALF + MARGIN / 2), -0.6, 0), Vector3.new(MARGIN, 1.2, G.Size * CELL) },
		{ CFrame.new(HALF + MARGIN / 2, -0.6, 0), Vector3.new(MARGIN, 1.2, G.Size * CELL) },
	}) do
		PartUtil.Part({ Size = side[2], Material = Enum.Material.SmoothPlastic, Color = trim, CFrame = origin * side[1], Parent = structure, Name = "Frame" })
	end
	-- bordo luminoso sottile
	for _, side in ipairs({
		{ CFrame.new(0, 0.05, -half + 0.3), Vector3.new(size, 0.3, 0.6) },
		{ CFrame.new(0, 0.05, half - 0.3), Vector3.new(size, 0.3, 0.6) },
		{ CFrame.new(-half + 0.3, 0.05, 0), Vector3.new(0.6, 0.3, size) },
		{ CFrame.new(half - 0.3, 0.05, 0), Vector3.new(0.6, 0.3, size) },
	}) do
		PartUtil.Part({ Size = side[2], Material = Enum.Material.Neon, Color = trim, Transparency = 0.35, CFrame = origin * side[1], Parent = structure, Name = "Rim", CanCollide = false, CastShadow = false })
	end
	-- isola rocciosa sotto la piattaforma (mesh; la collisione resta alle piastrelle) e nuvole
	local islandH = 24
	local islandMesh = MeshUtil.Make("island_plot", Vector3.new(size * 1.06, islandH, size * 1.06), { Material = Enum.Material.Slate, Color = Color3.fromRGB(150, 160, 190), CFrame = origin * CFrame.new(0, -1.0 - islandH * 0.405, 0), Parent = structure, Name = "Island" })
	if not islandMesh then
		PartUtil.Part({ Size = Vector3.new(size * 0.8, 6, size * 0.8), Material = Enum.Material.Slate, Color = Color3.fromRGB(150, 160, 190), CFrame = origin * CFrame.new(0, -4.2, 0), Parent = structure, Name = "Rock", CanCollide = false })
		PartUtil.Part({ Size = Vector3.new(size * 0.5, 7, size * 0.5), Material = Enum.Material.Slate, Color = Color3.fromRGB(130, 140, 175), CFrame = origin * CFrame.new(0, -10, 0) * CFrame.Angles(0, math.rad(20), 0), Parent = structure, Name = "Rock2", CanCollide = false })
		PartUtil.Part({ Size = Vector3.new(size * 0.22, 8, size * 0.22), Material = Enum.Material.Slate, Color = Color3.fromRGB(115, 125, 160), CFrame = origin * CFrame.new(0, -16, 0) * CFrame.Angles(0, math.rad(40), 0), Parent = structure, Name = "Rock3", CanCollide = false })
	end
	local rng = Random.new(math.floor(origin.X * 13 + origin.Z * 7))
	for i = 1, 7 do
		local a = (i / 7) * math.pi * 2 + rng:NextNumber(-0.3, 0.3)
		local r = half * rng:NextNumber(0.85, 1.05)
		PartUtil.Cloud(origin * CFrame.new(math.cos(a) * r, -3 + rng:NextNumber(-1.5, 1), math.sin(a) * r), rng:NextNumber(3.2, 4.8), structure, Color3.fromRGB(250, 252, 255), 0.02)
	end
end

function PlotBuilder:_buildStructures()
	local origin = self.Origin
	local structure = self.Folders.Structure
	local mode = self.Mode

	-- Pozza delle scintille (centro)
	local pozzaY = 0
	local hasCupola = false
	for _, m in ipairs((self.View.Layout and self.View.Layout.Modules) or {}) do
		if m.Id == "cupola" then
			hasCupola = true
		end
	end
	if hasCupola then
		local h = Defenses.EffectiveParams("cupola").Height or 7
		pozzaY = h
		local _ = MeshUtil.Make("pedestal", Vector3.new(8.6, h, 8.6), { Color = Color3.fromRGB(220, 200, 255), Material = Enum.Material.Glass, Transparency = 0.25, Reflectance = 0.2, CFrame = origin * CFrame.new(0, h / 2, 0), Parent = structure, Name = "Pedestal", CanCollide = true })
			or PartUtil.Cylinder(4.2, h, Color3.fromRGB(220, 200, 255), origin * CFrame.new(0, h / 2, 0), structure, { Material = Enum.Material.Glass, Transparency = 0.25, Reflectance = 0.2, Name = "Pedestal" })
		-- trampolini di luce intorno
		for i = 1, 3 do
			local a = (i / 3) * math.pi * 2 + math.rad(90)
			local pad = MeshUtil.Make("bounce_pad", Vector3.new(3.4, 0.5, 3.4), { Color = Color3.fromRGB(255, 200, 255), Material = Enum.Material.Neon, CFrame = origin * CFrame.new(math.cos(a) * 7.5, 0.25, math.sin(a) * 7.5), Parent = structure, Name = "BouncePad", CanCollide = true })
				or PartUtil.Cylinder(1.6, 0.4, Color3.fromRGB(255, 200, 255), origin * CFrame.new(math.cos(a) * 7.5, 0.2, math.sin(a) * 7.5), structure, { Material = Enum.Material.Neon, Name = "BouncePad" })
			pad:SetAttribute("Bounce", 95)
			PartUtil.Light(pad, Color3.fromRGB(255, 200, 255), 1, 10)
		end
	end
	local basin = MeshUtil.Make("basin", Vector3.new(7.6, 1.6, 7.6), { Color = Color3.fromRGB(236, 232, 220), Material = Enum.Material.Marble, CFrame = origin * CFrame.new(0, pozzaY + 0.8, 0), Parent = structure, Name = "PozzaBasin", CanCollide = true })
		or PartUtil.Cylinder(3.6, 1.4, Color3.fromRGB(236, 232, 220), origin * CFrame.new(0, pozzaY + 0.7, 0), structure, { Material = Enum.Material.Marble, Name = "PozzaBasin" })
	local water = PartUtil.Cylinder(2.65, 0.4, Color3.fromRGB(255, 205, 90), origin * CFrame.new(0, pozzaY + 1.3, 0), structure, { Material = Enum.Material.Neon, Transparency = 0.15, Name = "Pozza", CanCollide = false })
	water:SetAttribute("Interactive", true)
	PartUtil.Light(water, Color3.fromRGB(255, 200, 90), 1.6, 18)
	self.PozzaEmitter = PartUtil.Emitter(water, { Color = Color3.fromRGB(255, 225, 130), Rate = 8, Speed = NumberRange.new(1.5, 3.5), Lifetime = NumberRange.new(0.8, 1.6), Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.35), NumberSequenceKeypoint.new(1, 0) }), Name = "Sparks" })
	self.Pozza = water
	self.PozzaBasin = basin
	local _, exposedLabel = PartUtil.Billboard(water, { Size = UDim2.fromOffset(200, 50), Offset = Vector3.new(0, 3.2, 0), TextColor = Color3.fromRGB(255, 225, 130), MaxDistance = 120 })
	self.ExposedLabel = exposedLabel

	-- Ingresso (fronte, -Z) e Uscita (retro, +Z)
	local function pad(name, color, cf, transparency)
		return MeshUtil.Make("platform_pad", Vector3.new(6, 0.5, 6), { Color = color, Material = Enum.Material.Neon, Transparency = transparency, CFrame = cf * CFrame.new(0, 0.15, 0), Parent = structure, Name = name, CanCollide = true })
			or PartUtil.Cylinder(3, 0.4, color, cf * CFrame.new(0, 0.1, 0), structure, { Material = Enum.Material.Neon, Transparency = transparency, Name = name })
	end
	local entrance = pad("Entrance", Color3.fromRGB(150, 232, 200), origin * CFrame.new(0, 0, -(HALF + MARGIN / 2)), 0.2)
	self.Entrance = entrance
	local exitPad = pad("Exit", Color3.fromRGB(255, 170, 220), origin * CFrame.new(0, 0, HALF + MARGIN / 2), 0.2)
	self.Exit = exitPad
	-- arco dell'uscita
	for _, dx in ipairs({ -3.2, 3.2 }) do
		PartUtil.Part({ Size = Vector3.new(0.7, 7, 0.7), Color = Color3.fromRGB(250, 250, 255), CFrame = origin * CFrame.new(dx, 3.5, HALF + MARGIN / 2), Parent = structure, Name = "ExitPost" })
	end
	PartUtil.Part({ Size = Vector3.new(7.4, 0.7, 0.7), Color = Color3.fromRGB(250, 250, 255), CFrame = origin * CFrame.new(0, 7, HALF + MARGIN / 2), Parent = structure, Name = "ExitBeam" })
	local swirl = PartUtil.Part({ Size = Vector3.new(5.8, 6, 0.3), Color = Color3.fromRGB(255, 170, 220), Material = Enum.Material.ForceField, Transparency = 0.3, CFrame = origin * CFrame.new(0, 3.5, HALF + MARGIN / 2), Parent = structure, Name = "ExitSwirl", CanCollide = false, CanQuery = false })
	PartUtil.Light(swirl, Color3.fromRGB(255, 170, 220), 1, 14)
	PartUtil.Billboard(exitPad, { Size = UDim2.fromOffset(140, 36), Offset = Vector3.new(0, 8.5, 0), Text = "USCITA", TextColor = Color3.fromRGB(255, 190, 230) })
	PartUtil.Billboard(entrance, { Size = UDim2.fromOffset(140, 36), Offset = Vector3.new(0, 4, 0), Text = "INGRESSO", TextColor = Color3.fromRGB(170, 240, 215) })

	-- Cassaforte (lato sinistro) e pad di spawn (lato destro): solo per home/visit/demo
	if mode ~= "raid" then
		local vaultCF = origin * CFrame.new(-(HALF + MARGIN / 2), 0, 6)
		local vaultBody = MeshUtil.Make("vault", Vector3.new(5.4, 4.9, 5.4), { Color = Color3.fromRGB(120, 150, 210), Material = Enum.Material.Metal, Reflectance = 0.15, CFrame = vaultCF * CFrame.new(0, 2.45, 0), Parent = structure, Name = "VaultBody", CanCollide = true })
		if not vaultBody then
			vaultBody = PartUtil.Cylinder(2.6, 4.6, Color3.fromRGB(120, 150, 210), vaultCF * CFrame.new(0, 2.3, 0), structure, { Material = Enum.Material.Metal, Reflectance = 0.15, Name = "VaultBody" })
			PartUtil.Cylinder(2.8, 0.5, Color3.fromRGB(90, 115, 170), vaultCF * CFrame.new(0, 4.75, 0), structure, { Material = Enum.Material.Metal, Name = "VaultTop" })
		end
		local door = PartUtil.Part({ Size = Vector3.new(3.2, 3.2, 0.5), Color = Color3.fromRGB(150, 180, 235), Material = Enum.Material.Metal, CFrame = vaultCF * CFrame.new(0, 2.3, 2.5), Parent = structure, Name = "VaultDoor" })
		local dial = PartUtil.Cylinder(0.7, 0.4, Color3.fromRGB(255, 215, 110), vaultCF * CFrame.new(0, 2.3, 2.85) * CFrame.Angles(math.rad(90), 0, 0), structure, { Material = Enum.Material.Neon, Name = "VaultDial", CanCollide = false })
		PartUtil.Light(dial, Color3.fromRGB(255, 215, 110), 1, 10)
		self.Vault = vaultBody
		local _, vaultLabel = PartUtil.Billboard(vaultBody, { Size = UDim2.fromOffset(200, 50), Offset = Vector3.new(0, 4.2, 0), TextColor = Color3.fromRGB(190, 215, 255) })
		self.VaultLabel = vaultLabel
		if mode == "home" then
			local prompt = PartUtil.Prompt(door, Strings.PromptDeposit, "Cassaforte", 0, 12)
			prompt.Name = "DepositPrompt"
			self.DepositPrompt = prompt
		end

		local spawn = pad("SpawnPad", Color3.fromRGB(190, 230, 255), origin * CFrame.new(HALF + MARGIN / 2, 0, 6), 0.3)
		self.SpawnPad = spawn
		-- portale verso l'hub (lato destro, dietro lo spawn)
		local hubPad = PartUtil.Cylinder(2.2, 0.4, Color3.fromRGB(160, 200, 255), origin * CFrame.new(HALF + MARGIN / 2, 0.1, -12), structure, { Material = Enum.Material.Neon, Transparency = 0.2, Name = "HubPad" })
		local hubRing = PartUtil.Part({ Size = Vector3.new(5, 5, 0.4), Color = Color3.fromRGB(160, 200, 255), Material = Enum.Material.ForceField, Transparency = 0.35, CFrame = origin * CFrame.new(HALF + MARGIN / 2, 3, -12) * CFrame.Angles(0, math.rad(90), 0), Parent = structure, Name = "HubRing", CanCollide = false, CanQuery = false })
		PartUtil.Light(hubRing, Color3.fromRGB(160, 200, 255), 1, 14)
		PartUtil.Billboard(hubPad, { Size = UDim2.fromOffset(160, 36), Offset = Vector3.new(0, 6.5, 0), Text = "HUB", TextColor = Color3.fromRGB(200, 225, 255) })
		self.HubPad = hubPad

		-- targhetta del proprietario
		if self.View.OwnerName then
			local sign = PartUtil.Part({ Size = Vector3.new(0.4, 0.4, 0.4), Transparency = 1, CanCollide = false, CanQuery = false, CFrame = origin * CFrame.new(HALF + MARGIN / 2, 7, 22), Parent = structure, Name = "SignAnchor" })
			local plate = self.View.Nameplate and Cosmetics.Get(self.View.Nameplate)
			local text = self.View.OwnerName
			if plate and plate.Data.Text then
				text = text .. "\n" .. plate.Data.Text
			end
			PartUtil.Billboard(sign, { Size = UDim2.fromOffset(260, 70), Offset = Vector3.new(0, 0, 0), Text = text, TextColor = (plate and plate.Data.Color) or Color3.new(1, 1, 1), MaxDistance = 160 })
		end
	else
		-- in raid il pad di spawn è l'ingresso
		self.SpawnPad = entrance
	end
end

-- ───────────────────────── creature ─────────────────────────

function PlotBuilder:AddCreature(c)
	if self.CreatureModels[c.Uid] then
		self:RemoveCreature(c.Uid)
	end
	local model = CreatureModel.Build(c.Id, c.Variant, nil)
	if not model then
		return nil
	end
	model.Name = "Creature_" .. tostring(c.Uid)
	model:SetAttribute("Uid", c.Uid)
	model:SetAttribute("x", c.x)
	model:SetAttribute("z", c.z)
	model:PivotTo(self.Origin * CFrame.new(GridUtil.CellToLocal(c.x, c.z, 2.6)))
	local def = Creatures.Get(c.Id)
	local body = model.PrimaryPart
	local _, label = PartUtil.Billboard(body, { Size = UDim2.fromOffset(180, 56), Offset = Vector3.new(0, def.Visual.Size / 2 + 1.6, 0), TextColor = Color3.new(1, 1, 1), MaxDistance = 80 })
	label.Name = "Label"
	label.RichText = true
	if self.Mode == "home" then
		local prompt = PartUtil.Prompt(body, Strings.PromptCollect, def.Name, 0, 10)
		prompt.Name = "CollectPrompt"
		prompt:SetAttribute("Uid", c.Uid)
	end
	model.Parent = self.Folders.Creatures
	self.CreatureModels[c.Uid] = model
	self:SetCreatureBuffer(c.Uid, c.Buffer or 0, c.Id)
	return model
end

function PlotBuilder:RemoveCreature(uid)
	local m = self.CreatureModels[uid]
	if m then
		m:Destroy()
		self.CreatureModels[uid] = nil
	end
end

function PlotBuilder:SetCreatureBuffer(uid, buffer, creatureId)
	local m = self.CreatureModels[uid]
	if not m or not m.PrimaryPart then
		return
	end
	local def = Creatures.Get(creatureId or m:GetAttribute("CreatureId"))
	local label = m.PrimaryPart:FindFirstChild("Billboard") and m.PrimaryPart.Billboard:FindFirstChild("Label")
	if label then
		if buffer > 0 and self.Mode == "home" then
			label.Text = string.format('%s\n<font color="#FFD86A">+%d ✦</font>', def.Name, buffer)
		else
			label.Text = def.Name
		end
	end
	m:SetAttribute("Buffer", buffer)
	local prompt = m.PrimaryPart:FindFirstChild("CollectPrompt")
	if prompt then
		prompt.Enabled = buffer > 0
	end
end

-- ───────────────────────── moduli ─────────────────────────

function PlotBuilder:RebuildModules(layout)
	self.Folders.Modules:ClearAllChildren()
	-- ripristina piastrelle eventualmente trasformate in vuoto
	local skin = skinData(self.View.Skin)
	local mat = materialFromName(skin.Material)
	for key, tile in pairs(self.Tiles) do
		if tile:GetAttribute("Gap") then
			tile:SetAttribute("Gap", nil)
			tile.Transparency = 0
			tile.CanCollide = true
			tile.Material = mat
			local x, z = GridUtil.FromKey(key)
			local shade = ((x + z) % 2 == 0) and 1 or 0.92
			tile.Color = Color3.new(skin.Color.R * shade, skin.Color.G * shade, skin.Color.B * shade)
			tile.CustomPhysicalProperties = nil
		end
	end
	self.ModuleModels = {}
	for i, pm in ipairs((layout and layout.Modules) or {}) do
		local def = Defenses.Get(pm.Id)
		if def then
			local model = ModuleModel.Build(pm.Id, pm.Alt, self.Mode, nil)
			if model then
				local rot = pm.Rot or 0
				model:SetAttribute("Index", i)
				model:SetAttribute("x", pm.x)
				model:SetAttribute("z", pm.z)
				model:SetAttribute("Rot", rot)
				model:PivotTo(self.Origin * CFrame.new(GridUtil.CellToLocal(pm.x, pm.z, 0)) * CFrame.Angles(0, -rot * math.pi / 2, 0))
				model.Parent = self.Folders.Modules
				table.insert(self.ModuleModels, model)
				-- celle a vuoto
				if GAP_MODULES[pm.Id] then
					for _, c in ipairs(GridUtil.ModuleCells(Defenses.EffectiveFootprint(pm.Id, pm.Alt), pm.x, pm.z, rot)) do
						local tile = self.Tiles[GridUtil.Key(c.x, c.z)]
						if tile then
							tile:SetAttribute("Gap", true)
							tile.Transparency = (self.Mode == "raid") and 1 or 0.7
							tile.Material = Enum.Material.Glass
							tile.Color = Color3.fromRGB(90, 120, 180)
							tile.CanCollide = self.Mode ~= "raid"
						end
					end
				elseif pm.Id == "scivolo" then
					for _, c in ipairs(GridUtil.ModuleCells(def.Footprint, pm.x, pm.z, rot)) do
						local tile = self.Tiles[GridUtil.Key(c.x, c.z)]
						if tile then
							tile:SetAttribute("Gap", true) -- riutilizziamo il flag per il ripristino
							tile.CustomPhysicalProperties = PhysicalProperties.new(0.7, 0.05, 0.2, 100, 1)
						end
					end
				end
			end
		end
	end
end

-- ───────────────────────── decorazioni ─────────────────────────

function PlotBuilder:AddDecoration(d, index)
	local model = DecorationModel.Build(d.Id, nil, false)
	if not model then
		return nil
	end
	model:SetAttribute("Index", index)
	model:SetAttribute("x", d.x)
	model:SetAttribute("z", d.z)
	model:PivotTo(self.Origin * CFrame.new(GridUtil.CellToLocal(d.x, d.z, 0)) * CFrame.Angles(0, -(d.Rot or 0) * math.pi / 2, 0))
	model.Parent = self.Folders.Decorations
	return model
end

function PlotBuilder:RebuildDecorations(list)
	self.Folders.Decorations:ClearAllChildren()
	for i, d in ipairs(list or {}) do
		self:AddDecoration(d, i)
	end
end

-- ───────────────────────── etichette ─────────────────────────

function PlotBuilder:SetExposed(n)
	self.Exposed = n
	if self.ExposedLabel then
		self.ExposedLabel.Text = string.format("✦ %s esposte", Format.Number(n))
	end
	if self.PozzaEmitter then
		self.PozzaEmitter.Rate = math.clamp(4 + n / 25, 4, 40)
	end
end

function PlotBuilder:SetVault(cur, cap)
	if self.VaultLabel then
		self.VaultLabel.Text = string.format("🔒 %s / %s", Format.Number(cur), Format.Number(cap))
	end
end

function PlotBuilder:SetSkin(skinId)
	self.View.Skin = skinId
	local skin = skinData(skinId)
	local mat = materialFromName(skin.Material)
	for key, tile in pairs(self.Tiles) do
		if not tile:GetAttribute("Gap") then
			local x, z = GridUtil.FromKey(key)
			local shade = ((x + z) % 2 == 0) and 1 or 0.92
			tile.Material = mat
			tile.Color = Color3.new(skin.Color.R * shade, skin.Color.G * shade, skin.Color.B * shade)
		end
	end
	for _, p in ipairs(self.Folders.Structure:GetChildren()) do
		if p.Name == "Frame" or p.Name == "Rim" then
			p.Color = skin.Trim or Color3.new(1, 1, 1)
		end
	end
end

function PlotBuilder:SpawnCFrame()
	local pad = self.SpawnPad or self.Entrance
	return CFrame.new(pad.Position + Vector3.new(0, 4, 0)) * CFrame.Angles(0, math.rad(90), 0)
end

function PlotBuilder:EntranceCFrame()
	return CFrame.new(self.Entrance.Position + Vector3.new(0, 4, 0))
end

function PlotBuilder:Destroy()
	self.Model:Destroy()
end

return PlotBuilder
