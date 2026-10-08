--!nonstrict
local Config = require(script.Parent.Parent.Config)

local GridUtil = {}
local G = Config.Grid

function GridUtil.InBounds(x, z)
	return x >= 0 and z >= 0 and x < G.Size and z < G.Size
end

function GridUtil.Key(x, z)
	return x .. "," .. z
end

function GridUtil.FromKey(key)
	local x, z = key:match("^(%-?%d+),(%-?%d+)$")
	return tonumber(x), tonumber(z)
end

-- Centro di una cella in coordinate locali del plot (origine = centro del plot)
function GridUtil.CellToLocal(x, z, y)
	local half = G.Size * G.CellSize / 2
	return Vector3.new((x + 0.5) * G.CellSize - half, y or 0, (z + 0.5) * G.CellSize - half)
end

function GridUtil.CellToWorld(origin: CFrame, x, z, y)
	return origin:PointToWorldSpace(GridUtil.CellToLocal(x, z, y))
end

function GridUtil.WorldToCell(origin: CFrame, worldPos: Vector3)
	local localPos = origin:PointToObjectSpace(worldPos)
	local half = G.Size * G.CellSize / 2
	local x = math.floor((localPos.X + half) / G.CellSize)
	local z = math.floor((localPos.Z + half) / G.CellSize)
	return x, z
end

-- Ruota un footprint (lista di {dx,dz}) di rot*90° in senso orario
function GridUtil.RotateFootprint(footprint, rot)
	rot = (rot or 0) % 4
	local out = {}
	for _, cell in ipairs(footprint) do
		local dx, dz = cell[1], cell[2]
		for _ = 1, rot do
			dx, dz = -dz, dx
		end
		table.insert(out, { dx, dz })
	end
	return out
end

-- Celle occupate da un modulo con footprint, posizione e rotazione
function GridUtil.ModuleCells(footprint, cx, cz, rot)
	local out = {}
	for _, d in ipairs(GridUtil.RotateFootprint(footprint, rot)) do
		table.insert(out, { x = cx + d[1], z = cz + d[2] })
	end
	return out
end

function GridUtil.ReservedSet()
	local set = {}
	for _, list in ipairs({ G.EntranceCells, G.ExitCells, G.PozzaCells }) do
		for _, c in ipairs(list) do
			set[GridUtil.Key(c.x, c.z)] = true
		end
	end
	return set
end

return GridUtil
