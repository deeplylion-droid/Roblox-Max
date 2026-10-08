--!nonstrict
--[[
	MeshUtil: accesso ai template MeshPart caricati dal server (ReplicatedStorage.MeshTemplates).
	Make(key, dims, props) clona il template e lo dimensiona:
	  dims = numero          → dimensione massima = numero (proporzioni native)
	  dims = { Height = h }  → altezza = h (proporzioni native)
	  dims = { Width = w }   → larghezza X = w (proporzioni native)
	  dims = Vector3         → dimensione esplicita (anche non uniforme)
	Ritorna nil se il template non è disponibile: il chiamante usa le primitive di fallback.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local MeshUtil = {}
local folder

local function templates()
	if folder and folder.Parent then
		return folder
	end
	folder = ReplicatedStorage:FindFirstChild("MeshTemplates")
	return folder
end

function MeshUtil.Available(key)
	local f = templates()
	return f ~= nil and f:FindFirstChild(key) ~= nil
end

function MeshUtil.Count()
	local f = templates()
	return f and #f:GetChildren() or 0
end

local function computeSize(native: Vector3, dims)
	if typeof(dims) == "Vector3" then
		return dims
	end
	if type(dims) == "number" then
		local m = math.max(native.X, native.Y, native.Z)
		return native * (dims / math.max(m, 1e-6))
	end
	if type(dims) == "table" then
		if dims.Height then
			return native * (dims.Height / math.max(native.Y, 1e-6))
		elseif dims.Width then
			return native * (dims.Width / math.max(native.X, 1e-6))
		elseif dims.Depth then
			return native * (dims.Depth / math.max(native.Z, 1e-6))
		end
	end
	return native
end

function MeshUtil.Make(key, dims, props)
	local f = templates()
	local template = f and f:FindFirstChild(key)
	if not template then
		return nil
	end
	props = props or {}
	local part = template:Clone()
	part.Name = props.Name or key
	part.Anchored = true
	part.CanCollide = props.CanCollide == true
	part.CanTouch = props.CanTouch == true
	part.CanQuery = props.CanQuery ~= false
	part.CastShadow = props.CastShadow ~= false
	part.Material = props.Material or Enum.Material.SmoothPlastic
	part.Color = props.Color or Color3.new(1, 1, 1)
	part.Transparency = props.Transparency or 0
	part.Reflectance = props.Reflectance or 0
	local native = template:GetAttribute("NativeSize") or template.Size
	part.Size = computeSize(native, dims)
	if props.CFrame then
		part.CFrame = props.CFrame
	elseif props.Position then
		part.Position = props.Position
	end
	if props.Attributes then
		for k, v in pairs(props.Attributes) do
			part:SetAttribute(k, v)
		end
	end
	if props.Parent then
		part.Parent = props.Parent
	end
	return part
end

-- Posiziona la parte in modo che la sua base (Y minima) sia su `baseCF` (utile per oggetti appoggiati)
function MeshUtil.MakeOnGround(key, dims, baseCF: CFrame, props)
	props = props or {}
	local part = MeshUtil.Make(key, dims, props)
	if not part then
		return nil
	end
	part.CFrame = baseCF * CFrame.new(0, part.Size.Y / 2, 0)
	return part
end

return MeshUtil
