--!nonstrict
--[[
	BuildController: modalità costruzione nel proprio vivaio.
	Griglia visibile, fantasma del modulo/creatura/decorazione, rotazione, anteprima del
	percorso (validatore condiviso), energia difensiva. Mobile-first: tocco = posiziona.
	I moduli si modificano in un layout di lavoro e si pubblicano in un colpo solo.
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local Workspace = game:GetService("Workspace")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Defenses = require(Shared.Catalog.Defenses)
local Creatures = require(Shared.Catalog.Creatures)
local LayoutValidator = require(Shared.LayoutValidator)
local GridUtil = require(Shared.Util.GridUtil)
local TableUtil = require(Shared.Util.TableUtil)
local Signal = require(Shared.Util.Signal)
local Net = require(Shared.Util.Net)
local PartUtil = require(Shared.Models.PartUtil)
local ModuleModel = require(Shared.Models.ModuleModel)
local CreatureModel = require(Shared.Models.CreatureModel)
local DecorationModel = require(Shared.Models.DecorationModel)
local State = require(script.Parent.State)
local Audio = require(script.Parent.Audio)

local Build = {}
Build.Active = false
Build.Mode = nil -- "creature" | "module" | "decoration" | "edit"
Build.Payload = nil
Build.Rot = 0
Build.Layout = { Modules = {} } -- layout di lavoro
Build.Changed = Signal.new() -- (result: Validator.Result)
Build.ModeChanged = Signal.new()
Build.Toast = nil -- impostato da Main

local player = Players.LocalPlayer
local camera = Workspace.CurrentCamera
local folder -- parti locali (griglia, fantasma, evidenziazioni)
local ghost
local cursor
local gridParts = {}
local pathParts = {}
local hoverCell = nil
local renderConn
local CELL = Config.Grid.CellSize

local function myPlot()
	local plots = Workspace:FindFirstChild("Plots")
	if not plots then
		return nil
	end
	for _, m in ipairs(plots:GetChildren()) do
		if m:GetAttribute("OwnerUserId") == player.UserId then
			return m
		end
	end
	return nil
end

local function origin()
	local plot = myPlot()
	return plot and plot:GetAttribute("Origin")
end

local function ensureFolder()
	if folder and folder.Parent then
		return folder
	end
	folder = Instance.new("Folder")
	folder.Name = "BuildLocal"
	folder.Parent = Workspace
	return folder
end

local function clearGhost()
	if ghost then
		ghost:Destroy()
		ghost = nil
	end
end

local function buildGrid()
	for _, p in ipairs(gridParts) do
		p:Destroy()
	end
	gridParts = {}
	local o = origin()
	if not o then
		return
	end
	local half = Config.Grid.Size * CELL / 2
	for i = 0, Config.Grid.Size do
		local offset = -half + i * CELL
		local a = PartUtil.Part({ Size = Vector3.new(0.12, 0.08, Config.Grid.Size * CELL), Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.Neon, Transparency = 0.45, CanCollide = false, CanQuery = false, CFrame = o * CFrame.new(offset, 0.06, 0), Parent = ensureFolder(), Name = "GridLine", CastShadow = false })
		local b = PartUtil.Part({ Size = Vector3.new(Config.Grid.Size * CELL, 0.08, 0.12), Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.Neon, Transparency = 0.45, CanCollide = false, CanQuery = false, CFrame = o * CFrame.new(0, 0.06, offset), Parent = folder, Name = "GridLine", CastShadow = false })
		table.insert(gridParts, a)
		table.insert(gridParts, b)
	end
	-- celle riservate evidenziate (ingresso/pozza/uscita)
	for key in pairs(GridUtil.ReservedSet()) do
		local x, z = GridUtil.FromKey(key)
		local p = PartUtil.Part({ Size = Vector3.new(CELL - 0.3, 0.06, CELL - 0.3), Color = Color3.fromRGB(255, 190, 230), Material = Enum.Material.Neon, Transparency = 0.7, CanCollide = false, CanQuery = false, CFrame = o * CFrame.new(GridUtil.CellToLocal(x, z, 0.08)), Parent = folder, Name = "Reserved", CastShadow = false })
		table.insert(gridParts, p)
	end
end

local function context()
	local creatureCells, decoCells = {}, {}
	for uid, c in pairs(State.Get("Creatures") or {}) do
		if c.x ~= nil and not (Build.Mode == "creature" and Build.Payload and Build.Payload.Uid == uid) then
			creatureCells[GridUtil.Key(c.x, c.z)] = true
		end
	end
	for _, d in ipairs((State.Get("Decorations") or { Placed = {} }).Placed or {}) do
		decoCells[GridUtil.Key(d.x, d.z)] = true
	end
	return {
		UnlockedModules = State.Get("UnlockedModules"),
		UnlockedAlternatives = State.Get("UnlockedAlternatives"),
		CreatureCells = creatureCells,
		DecorationCells = decoCells,
	}
end

function Build.Validate()
	return LayoutValidator.Validate(Build.Layout, context())
end

local function refreshPath()
	for _, p in ipairs(pathParts) do
		p:Destroy()
	end
	pathParts = {}
	local o = origin()
	if not o or not Build.Active then
		return
	end
	local result = Build.Validate()
	if result.Path then
		for _, cell in ipairs(result.Path) do
			local p = PartUtil.Part({ Size = Vector3.new(CELL - 1.2, 0.06, CELL - 1.2), Color = Color3.fromRGB(140, 240, 180), Material = Enum.Material.Neon, Transparency = 0.6, CanCollide = false, CanQuery = false, CFrame = o * CFrame.new(GridUtil.CellToLocal(cell.x, cell.z, 0.1)), Parent = ensureFolder(), Name = "Path", CastShadow = false })
			table.insert(pathParts, p)
		end
	end
	-- moduli del layout di lavoro non ancora pubblicati: fantasmi fissi
	for _, pm in ipairs(Build.Layout.Modules) do
		local m = ModuleModel.Build(pm.Id, pm.Alt, "ghost", nil)
		if m then
			m.Name = "Working_" .. pm.Id
			m:PivotTo(o * CFrame.new(GridUtil.CellToLocal(pm.x, pm.z, 0)) * CFrame.Angles(0, -(pm.Rot or 0) * math.pi / 2, 0))
			for _, d in ipairs(m:GetDescendants()) do
				if d:IsA("BasePart") then
					d.Color = d.Color:Lerp(Color3.fromRGB(120, 200, 255), 0.5)
				end
			end
			m.Parent = folder
			table.insert(pathParts, m)
		end
	end
	Build.Changed:Fire(result)
end

local function occupiedByWorking()
	local set = {}
	for _, pm in ipairs(Build.Layout.Modules) do
		for _, c in ipairs(GridUtil.ModuleCells(Defenses.EffectiveFootprint(pm.Id, pm.Alt), pm.x, pm.z, pm.Rot or 0)) do
			set[GridUtil.Key(c.x, c.z)] = true
		end
	end
	return set
end

local function cellFree(x, z)
	if not GridUtil.InBounds(x, z) then
		return false
	end
	local key = GridUtil.Key(x, z)
	if GridUtil.ReservedSet()[key] then
		return false
	end
	local ctx = context()
	if ctx.CreatureCells[key] or ctx.DecorationCells[key] then
		return false
	end
	if occupiedByWorking()[key] then
		return false
	end
	return true
end

local function canPlaceAt(x, z)
	if Build.Mode == "module" then
		local test = TableUtil.DeepCopy(Build.Layout)
		table.insert(test.Modules, { Id = Build.Payload.Id, x = x, z = z, Rot = Build.Rot, Alt = Build.Payload.Alt })
		local res = LayoutValidator.Validate(test, context())
		return res.Ok, res.Reason
	end
	return cellFree(x, z), "Cella occupata"
end

local function makeGhost()
	clearGhost()
	if Build.Mode == "module" then
		ghost = ModuleModel.Build(Build.Payload.Id, Build.Payload.Alt, "ghost", nil)
	elseif Build.Mode == "creature" then
		local c = (State.Get("Creatures") or {})[Build.Payload.Uid]
		if c then
			ghost = CreatureModel.Build(c.Id, c.Variant, nil)
			for _, d in ipairs(ghost:GetDescendants()) do
				if d:IsA("BasePart") then
					d.Transparency = math.max(d.Transparency, 0.4)
					d.CanCollide = false
					d.CanQuery = false
				elseif d:IsA("ParticleEmitter") then
					d.Enabled = false
				end
			end
		end
	elseif Build.Mode == "decoration" then
		ghost = DecorationModel.Build(Build.Payload.Id, nil, true)
	end
	if ghost then
		ghost.Name = "Ghost"
		ghost.Parent = ensureFolder()
	end
	if not cursor then
		cursor = PartUtil.Part({ Size = Vector3.new(CELL - 0.2, 0.1, CELL - 0.2), Color = Color3.fromRGB(140, 240, 180), Material = Enum.Material.Neon, Transparency = 0.4, CanCollide = false, CanQuery = false, CFrame = CFrame.new(0, -100, 0), Parent = ensureFolder(), Name = "Cursor", CastShadow = false })
	end
end

local function pointerPosition()
	if UserInputService.TouchEnabled and not UserInputService.MouseEnabled then
		return nil -- su touch usiamo solo il tap
	end
	return UserInputService:GetMouseLocation()
end

local function cellFromScreen(pos)
	local plot = myPlot()
	local o = origin()
	if not plot or not o then
		return nil
	end
	local ray = camera:ViewportPointToRay(pos.X, pos.Y)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Include
	params.FilterDescendantsInstances = { plot.Tiles }
	local hit = Workspace:Raycast(ray.Origin, ray.Direction * 500, params)
	if not hit then
		return nil
	end
	local x, z = GridUtil.WorldToCell(o, hit.Position)
	if GridUtil.InBounds(x, z) then
		return x, z
	end
	return nil
end

local function updateGhost(x, z)
	hoverCell = x and { x = x, z = z } or nil
	local o = origin()
	if not o or not x then
		if cursor then
			cursor.CFrame = CFrame.new(0, -100, 0)
		end
		if ghost then
			ghost:PivotTo(CFrame.new(0, -100, 0))
		end
		return
	end
	local ok = canPlaceAt(x, z)
	if cursor then
		cursor.CFrame = o * CFrame.new(GridUtil.CellToLocal(x, z, 0.12))
		cursor.Color = ok and Color3.fromRGB(140, 240, 180) or Color3.fromRGB(240, 120, 120)
	end
	if ghost then
		local y = Build.Mode == "creature" and 2.6 or 0
		ghost:PivotTo(o * CFrame.new(GridUtil.CellToLocal(x, z, y)) * CFrame.Angles(0, -Build.Rot * math.pi / 2, 0))
	end
end

local function hitExisting(pos)
	local plot = myPlot()
	if not plot then
		return nil
	end
	local ray = camera:ViewportPointToRay(pos.X, pos.Y)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Include
	params.FilterDescendantsInstances = { plot.Creatures, plot.Decorations, ensureFolder() }
	local hit = Workspace:Raycast(ray.Origin, ray.Direction * 500, params)
	if not hit then
		return nil
	end
	local inst = hit.Instance
	while inst and inst ~= Workspace do
		if inst:IsA("Model") and (inst:GetAttribute("Uid") or inst:GetAttribute("DecorationId") or inst.Name:match("^Working_")) then
			return inst
		end
		inst = inst.Parent
	end
	return nil
end

local function tryPlace(pos)
	if not Build.Active then
		return
	end
	if Build.Mode == "edit" then
		local model = hitExisting(pos)
		if not model then
			return
		end
		if model:GetAttribute("Uid") then
			Build.Enter("creature", { Uid = model:GetAttribute("Uid") })
			return
		end
		if model:GetAttribute("DecorationId") then
			local index = model:GetAttribute("Index")
			if index then
				local ok, msg = Net.Invoke("RemoveDecoration", index)
				if not ok and Build.Toast then
					Build.Toast(msg or Strings.Error, "warning")
				end
			end
			return
		end
		if model.Name:match("^Working_") then
			-- rimuove il modulo del layout di lavoro sotto il puntatore
			local o = origin()
			local x, z = GridUtil.WorldToCell(o, model:GetPivot().Position)
			for i, pm in ipairs(Build.Layout.Modules) do
				for _, c in ipairs(GridUtil.ModuleCells(Defenses.EffectiveFootprint(pm.Id, pm.Alt), pm.x, pm.z, pm.Rot or 0)) do
					if c.x == x and c.z == z then
						table.remove(Build.Layout.Modules, i)
						Audio.Play("Click")
						refreshPath()
						return
					end
				end
			end
		end
		return
	end
	local x, z = cellFromScreen(pos)
	if not x then
		return
	end
	local ok, reason = canPlaceAt(x, z)
	if not ok then
		Audio.Play("Error")
		if Build.Toast then
			Build.Toast(reason or "Posizione non valida", "warning")
		end
		return
	end
	if Build.Mode == "module" then
		table.insert(Build.Layout.Modules, { Id = Build.Payload.Id, x = x, z = z, Rot = Build.Rot, Alt = Build.Payload.Alt })
		Audio.Play("Place")
		refreshPath()
		-- resta in modalità per piazzare altri moduli? Passa a edit per evitare piazzamenti accidentali
		Build.Enter("edit")
	elseif Build.Mode == "creature" then
		local okS, msg = Net.Invoke("PlaceCreature", Build.Payload.Uid, x, z)
		if okS then
			Build.Enter("edit")
		elseif Build.Toast then
			Build.Toast(msg or Strings.Error, "warning")
		end
	elseif Build.Mode == "decoration" then
		local okS, msg = Net.Invoke("PlaceDecoration", Build.Payload.Id, x, z, Build.Rot)
		if okS then
			Build.Enter("edit")
		elseif Build.Toast then
			Build.Toast(msg or Strings.Error, "warning")
		end
	end
end

function Build.Rotate()
	Build.Rot = (Build.Rot + 1) % 4
	if hoverCell then
		updateGhost(hoverCell.x, hoverCell.z)
	end
	Audio.Play("Click")
end

function Build.Enter(mode, payload)
	if not Build.Active then
		Build.Start()
	end
	if not Build.Active then
		return -- non nel proprio vivaio
	end
	Build.Mode = mode
	Build.Payload = payload
	Build.Rot = 0
	makeGhost()
	if mode == "edit" then
		clearGhost()
	end
	Build.ModeChanged:Fire(mode, payload)
end

function Build.Start()
	if Build.Active then
		return
	end
	if not myPlot() then
		if Build.Toast then
			Build.Toast("Torna nel tuo vivaio per costruire", "warning")
		end
		return
	end
	Build.Active = true
	Build.Layout = TableUtil.DeepCopy(State.Get("Layout") or State.Get("LastValidLayout") or { Modules = {} })
	if #Build.Layout.Modules == 0 and State.Get("LastValidLayout") then
		Build.Layout = TableUtil.DeepCopy(State.Get("LastValidLayout"))
	end
	ensureFolder()
	buildGrid()
	refreshPath()
	Build.Mode = "edit"
	renderConn = RunService.RenderStepped:Connect(function()
		local pos = pointerPosition()
		if pos then
			local x, z = cellFromScreen(pos)
			updateGhost(x, z)
		end
	end)
	Build.ModeChanged:Fire("edit")
end

function Build.Stop()
	if not Build.Active then
		return
	end
	Build.Active = false
	Build.Mode = nil
	if renderConn then
		renderConn:Disconnect()
		renderConn = nil
	end
	clearGhost()
	if folder then
		folder:Destroy()
		folder = nil
		cursor = nil
	end
	gridParts, pathParts = {}, {}
	Build.ModeChanged:Fire(nil)
end

function Build.Publish()
	local result = Build.Validate()
	if not result.Ok then
		if Build.Toast then
			Build.Toast(result.Reason or Strings.BuildPathBlocked, "warning")
		end
		Audio.Play("Error")
		return false
	end
	local ok, msg = Net.Invoke("SaveLayout", Build.Layout)
	if not ok and Build.Toast then
		Build.Toast(type(msg) == "string" and msg or Strings.Error, "warning")
	end
	return ok
end

function Build.RestoreLastValid()
	Build.Layout = TableUtil.DeepCopy(State.Get("LastValidLayout") or { Modules = {} })
	refreshPath()
end

function Build.Clear()
	Build.Layout = { Modules = {} }
	refreshPath()
end

function Build.SetLayout(layout)
	Build.Layout = TableUtil.DeepCopy(layout)
	refreshPath()
end

function Build.Init()
	UserInputService.InputBegan:Connect(function(input, processed)
		if not Build.Active then
			return
		end
		if input.UserInputType == Enum.UserInputType.MouseButton1 and not processed then
			tryPlace(UserInputService:GetMouseLocation())
		elseif input.KeyCode == Enum.KeyCode.R then
			Build.Rotate()
		elseif input.KeyCode == Enum.KeyCode.X then
			Build.Enter("edit")
		elseif input.KeyCode == Enum.KeyCode.Escape then
			Build.Stop()
		end
	end)
	UserInputService.TouchTap:Connect(function(positions, processed)
		if not Build.Active or processed then
			return
		end
		local p = positions[1]
		if p then
			local pos = Vector2.new(p.X, p.Y)
			local x, z = cellFromScreen(pos)
			updateGhost(x, z)
			tryPlace(pos)
		end
	end)
	-- aggiorna l'anteprima quando il server conferma modifiche
	State.Changed:Connect(function(key)
		if Build.Active and (key == "Creatures" or key == "Decorations" or key == "LastValidLayout" or key == "UnlockedModules") then
			if key == "LastValidLayout" then
				Build.Layout = TableUtil.DeepCopy(State.Get("LastValidLayout"))
			end
			refreshPath()
		end
	end)
	-- esci dalla costruzione se il giocatore lascia il vivaio
	player:GetAttributeChangedSignal("Location"):Connect(function()
		if player:GetAttribute("Location") ~= "home" then
			Build.Stop()
		end
	end)
end

return Build
