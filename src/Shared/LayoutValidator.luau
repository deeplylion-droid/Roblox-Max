--!nonstrict
--[[
	LayoutValidator: usato sia dal client (anteprima) sia dal server (autorità).
	Verifica: formato, moduli esistenti e sbloccati, limiti per categoria, budget energia,
	celle in griglia, nessuna sovrapposizione (moduli, creature, decorazioni, celle riservate)
	e che esista almeno un percorso completabile: ingresso → pozza → uscita
	attraverso celle non solide (BFS a 4 direzioni).
]]

local Config = require(script.Parent.Config)
local Defenses = require(script.Parent.Catalog.Defenses)
local GridUtil = require(script.Parent.Util.GridUtil)

local Validator = {}
local G = Config.Grid

export type PlacedModule = { Id: string, x: number, z: number, Rot: number?, Alt: string? }
export type Layout = { Modules: { PlacedModule } }
export type Result = {
	Ok: boolean,
	Reason: string?,
	Energy: number,
	Counts: { ostacolo: number, distrazione: number, firma: number },
	Difficulty: number,
	Path: { { x: number, z: number } }?, -- percorso trovato (per anteprima)
	Occupied: { [string]: string }, -- cella -> moduleId
}

local function neighbors(x, z)
	return { { x + 1, z }, { x - 1, z }, { x, z + 1 }, { x, z - 1 } }
end

-- BFS da un insieme di celle sorgente a un insieme bersaglio; restituisce il percorso o nil
local function bfs(solid, sources, targets)
	local targetSet = {}
	for _, c in ipairs(targets) do
		targetSet[GridUtil.Key(c.x, c.z)] = true
	end
	local visited, parent, queue = {}, {}, {}
	for _, c in ipairs(sources) do
		local k = GridUtil.Key(c.x, c.z)
		if not solid[k] then
			visited[k] = true
			table.insert(queue, { c.x, c.z })
		end
	end
	local head = 1
	while head <= #queue do
		local cur = queue[head]
		head += 1
		local ck = GridUtil.Key(cur[1], cur[2])
		if targetSet[ck] then
			local path = {}
			local k = ck
			while k do
				local px, pz = GridUtil.FromKey(k)
				table.insert(path, 1, { x = px, z = pz })
				k = parent[k]
			end
			return path
		end
		for _, n in ipairs(neighbors(cur[1], cur[2])) do
			local nx, nz = n[1], n[2]
			if GridUtil.InBounds(nx, nz) then
				local nk = GridUtil.Key(nx, nz)
				if not visited[nk] and not solid[nk] then
					visited[nk] = true
					parent[nk] = ck
					table.insert(queue, { nx, nz })
				end
			end
		end
	end
	return nil
end

--[[
	layout: Layout
	context: {
		UnlockedModules: {[id]=true}?,  -- se nil, non controlla gli sblocchi (anteprima)
		UnlockedAlternatives: {[moduleId]={[alt]=true}}?,
		CreatureCells: {[key]=true}?,
		DecorationCells: {[key]=true}?,
	}
]]
function Validator.Validate(layout, context): Result
	context = context or {}
	local result: Result = {
		Ok = false,
		Reason = nil,
		Energy = 0,
		Counts = { ostacolo = 0, distrazione = 0, firma = 0 },
		Difficulty = 0,
		Path = nil,
		Occupied = {},
	}

	if type(layout) ~= "table" or type(layout.Modules) ~= "table" then
		result.Reason = "Formato layout non valido"
		return result
	end
	if #layout.Modules > 6 then
		result.Reason = "Troppi moduli (massimo 6)"
		return result
	end

	local reserved = GridUtil.ReservedSet()
	local solid = {}

	for i, pm in ipairs(layout.Modules) do
		if type(pm) ~= "table" or type(pm.Id) ~= "string" or type(pm.x) ~= "number" or type(pm.z) ~= "number" then
			result.Reason = "Modulo #" .. i .. " malformato"
			return result
		end
		local def = Defenses.Get(pm.Id)
		if not def then
			result.Reason = "Modulo sconosciuto: " .. tostring(pm.Id)
			return result
		end
		if pm.x ~= math.floor(pm.x) or pm.z ~= math.floor(pm.z) then
			result.Reason = "Coordinate non intere"
			return result
		end
		local rot = pm.Rot or 0
		if type(rot) ~= "number" or rot < 0 or rot > 3 or rot ~= math.floor(rot) then
			result.Reason = "Rotazione non valida"
			return result
		end
		if pm.Alt ~= nil then
			if type(pm.Alt) ~= "string" then
				result.Reason = "Alternativa non valida"
				return result
			end
			if pm.Alt ~= "base" and not Defenses.GetAlternative(pm.Id, pm.Alt) then
				result.Reason = "Alternativa sconosciuta per " .. def.Name
				return result
			end
			if context.UnlockedAlternatives and pm.Alt ~= "base" then
				local set = context.UnlockedAlternatives[pm.Id]
				if not (set and set[pm.Alt]) then
					result.Reason = "Alternativa non sbloccata: " .. pm.Alt
					return result
				end
			end
		end
		if context.UnlockedModules and not context.UnlockedModules[pm.Id] then
			result.Reason = def.Name .. " non è sbloccato"
			return result
		end

		result.Counts[def.Category] += 1
		result.Energy += def.Energy
		result.Difficulty += def.Difficulty

		local cells = GridUtil.ModuleCells(Defenses.EffectiveFootprint(pm.Id, pm.Alt), pm.x, pm.z, rot)
		for _, c in ipairs(cells) do
			if not GridUtil.InBounds(c.x, c.z) then
				result.Reason = def.Name .. " esce dalla griglia"
				return result
			end
			local k = GridUtil.Key(c.x, c.z)
			if reserved[k] then
				result.Reason = def.Name .. " occupa una cella riservata (ingresso, pozza o uscita)"
				return result
			end
			if result.Occupied[k] then
				result.Reason = def.Name .. " si sovrappone a un altro modulo"
				return result
			end
			if context.CreatureCells and context.CreatureCells[k] then
				result.Reason = def.Name .. " si sovrappone a una creatura"
				return result
			end
			if context.DecorationCells and context.DecorationCells[k] then
				result.Reason = def.Name .. " si sovrappone a una decorazione"
				return result
			end
			result.Occupied[k] = pm.Id
			if def.Solid then
				solid[k] = true
			end
		end
	end

	local D = Config.Defense
	if result.Counts.ostacolo > D.MaxObstacles then
		result.Reason = "Troppi ostacoli (massimo " .. D.MaxObstacles .. ")"
		return result
	end
	if result.Counts.distrazione > D.MaxDistractions then
		result.Reason = "Troppe distrazioni (massimo " .. D.MaxDistractions .. ")"
		return result
	end
	if result.Counts.firma > D.MaxSignature then
		result.Reason = "Un solo modulo firma"
		return result
	end
	if result.Energy > D.EnergyBudget then
		result.Reason = "Energia difensiva insufficiente (" .. result.Energy .. "/" .. D.EnergyBudget .. ")"
		return result
	end

	-- Percorso: ingresso → pozza → uscita
	local toPozza = bfs(solid, G.EntranceCells, G.PozzaCells)
	if not toPozza then
		result.Reason = "Nessun percorso dall'ingresso alla pozza"
		return result
	end
	local toExit = bfs(solid, G.PozzaCells, G.ExitCells)
	if not toExit then
		result.Reason = "Nessun percorso dalla pozza all'uscita"
		return result
	end
	local path = table.clone(toPozza)
	for i = 2, #toExit do
		table.insert(path, toExit[i])
	end
	result.Path = path
	result.Ok = true
	return result
end

-- Stima difficoltà 1..5 ("nuvole") a partire dal peso dei moduli
function Validator.DifficultyStars(difficultySum)
	if difficultySum <= 0 then
		return 1
	end
	return math.clamp(math.floor(difficultySum / 2.2) + 1, 1, 5)
end

-- Layout vuoto
function Validator.Empty(): Layout
	return { Modules = {} }
end

return Validator
