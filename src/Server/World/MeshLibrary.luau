--!nonstrict
--[[
	MeshLibrary: carica all'avvio gli asset Model (mesh glTF caricate via Open Cloud) con
	InsertService e ne espone i MeshPart come template in ReplicatedStorage.MeshTemplates.
	Se un asset non è disponibile (place di un altro proprietario, asset rimosso, Studio offline),
	i costruttori usano automaticamente le primitive di fallback.
]]
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local MeshAssets = require(ReplicatedStorage.Shared.Catalog.MeshAssets)
local Logger = require(script.Parent.Parent.Util.Logger)

local MeshLibrary = { Loaded = 0, Failed = {} }

local function findMeshPart(inst)
	if inst:IsA("MeshPart") then
		return inst
	end
	for _, d in ipairs(inst:GetDescendants()) do
		if d:IsA("MeshPart") then
			return d
		end
	end
	return nil
end

function MeshLibrary.Preload(timeout)
	local folder = ReplicatedStorage:FindFirstChild("MeshTemplates") or Instance.new("Folder")
	folder.Name = "MeshTemplates"
	folder.Parent = ReplicatedStorage
	local pending = 0
	for key, info in pairs(MeshAssets) do
		pending += 1
		task.spawn(function()
			local ok, result = pcall(function()
				return InsertService:LoadAsset(info.AssetId)
			end)
			if ok and result then
				local mp = findMeshPart(result)
				if mp then
					local template = mp:Clone()
					template.Name = key
					template.Anchored = true
					template.CanCollide = false
					template.CanTouch = false
					template:ClearAllChildren()
					template:SetAttribute("NativeSize", template.Size)
					template:SetAttribute("AssetId", info.AssetId)
					template.Parent = folder
					MeshLibrary.Loaded += 1
				else
					MeshLibrary.Failed[key] = "nessun MeshPart nel modello"
				end
				result:Destroy()
			else
				MeshLibrary.Failed[key] = tostring(result)
			end
			pending -= 1
		end)
	end
	local t0 = os.clock()
	while pending > 0 and os.clock() - t0 < (timeout or 25) do
		task.wait(0.1)
	end
	local total = 0
	for _ in pairs(MeshAssets) do
		total += 1
	end
	if MeshLibrary.Loaded < total then
		Logger.Warn("Mesh", string.format("Template mesh caricati %d/%d: per i mancanti si usano le primitive.", MeshLibrary.Loaded, total))
		for k, why in pairs(MeshLibrary.Failed) do
			Logger.Warn("Mesh", "  -", k, why)
		end
	else
		Logger.Info("Mesh", string.format("Template mesh caricati %d/%d", MeshLibrary.Loaded, total))
	end
	return MeshLibrary.Loaded
end

return MeshLibrary
