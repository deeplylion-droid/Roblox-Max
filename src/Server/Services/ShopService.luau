--!nonstrict
--[[
	ShopService: cosmetici con gettoni stile, acquisti Robux opzionali (DeveloperProduct),
	Pass delle Nuvole trasparente, bundle fondatore (gamepass). Tutto idempotente via Ledger.
	Nessun acquisto tocca produzione, raid o protezioni.
]]
local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Cosmetics = require(Shared.Catalog.Cosmetics)
local Decorations = require(Shared.Catalog.Decorations)
local Net = require(Shared.Util.Net)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)
local Logger = require(script.Parent.Parent.Util.Logger)

local ShopService = {}

local function ps()
	return Registry.Get("PlayerService")
end

function ShopService.GrantCosmetic(player, profile, cosmeticId, reason)
	local c = Cosmetics.Get(cosmeticId)
	if not c then
		return false
	end
	if profile.Cosmetics.Owned[cosmeticId] then
		return false
	end
	profile.Cosmetics.Owned[cosmeticId] = true
	ps().Sync(player, "Cosmetics")
	Logger.Audit("Shop", player, "grant", cosmeticId .. " (" .. (reason or "?") .. ")")
	return true
end

function ShopService.Buy(player, id)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	id = Guard.Str(id, 48)
	if not id then
		return false, Strings.Error
	end
	-- decorazioni acquistabili con gettoni
	local deco = Decorations.ById[id]
	if deco and deco.TokenPrice then
		if profile.Decorations.Owned[id] then
			return false, Strings.ShopOwned
		end
		if profile.StyleTokens < deco.TokenPrice then
			return false, "Gettoni insufficienti"
		end
		profile.StyleTokens -= deco.TokenPrice
		Registry.Get("EconomyService").GrantDecoration(player, profile, id)
		ps().Sync(player, "StyleTokens", "Decorations")
		ps().Sound(player, "Success")
		return true
	end
	local c = Cosmetics.Get(id)
	if not c then
		return false, Strings.Error
	end
	if profile.Cosmetics.Owned[id] then
		return false, Strings.ShopOwned
	end
	if not c.TokenPrice then
		return false, "Non acquistabile con gettoni"
	end
	if profile.StyleTokens < c.TokenPrice then
		return false, "Gettoni insufficienti"
	end
	profile.StyleTokens -= c.TokenPrice
	ShopService.GrantCosmetic(player, profile, id, "tokens")
	ps().Sync(player, "StyleTokens")
	ps().Sound(player, "Success")
	ps().Toast(player, string.format("Acquistato: %s", c.Name), "success")
	return true
end

function ShopService.Equip(player, id)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	id = Guard.Str(id, 48)
	local c = id and Cosmetics.Get(id)
	if not c then
		return false, Strings.Error
	end
	if not profile.Cosmetics.Owned[id] then
		return false, "Non posseduto"
	end
	profile.Cosmetics.Equipped[c.Slot] = id
	ps().Sync(player, "Cosmetics")
	if c.Slot == "skin" then
		Registry.Get("PlotService").RefreshSkin(player)
	elseif c.Slot == "nameplate" then
		Registry.Get("PlotService").Rebuild(player)
	end
	player:SetAttribute("Trail", profile.Cosmetics.Equipped.trail)
	player:SetAttribute("Nameplate", profile.Cosmetics.Equipped.nameplate)
	Registry.Get("GalleryService").MarkDirty(player)
	return true
end

-- ───────────────────────── Pass delle Nuvole ─────────────────────────

function ShopService.ClaimPassTier(player, tierIndex)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	tierIndex = Guard.Int(tierIndex, 1, #Cosmetics.Pass.Tiers)
	local tier = tierIndex and Cosmetics.Pass.Tiers[tierIndex]
	if not tier then
		return false, Strings.Error
	end
	if profile.Pass.Points < tier.Points then
		return false, "Punti pass insufficienti"
	end
	local granted = false
	local eco = Registry.Get("EconomyService")
	if not profile.Pass.ClaimedFree[tostring(tierIndex)] then
		profile.Pass.ClaimedFree[tostring(tierIndex)] = true
		if tier.Free.Tokens then
			eco.GrantTokens(player, profile, tier.Free.Tokens, "pass")
		end
		if tier.Free.Cosmetic then
			ShopService.GrantCosmetic(player, profile, tier.Free.Cosmetic, "pass")
		end
		granted = true
	end
	if profile.Pass.Premium and not profile.Pass.ClaimedPremium[tostring(tierIndex)] then
		profile.Pass.ClaimedPremium[tostring(tierIndex)] = true
		if tier.Premium.Tokens then
			eco.GrantTokens(player, profile, tier.Premium.Tokens, "pass_premium")
		end
		if tier.Premium.Cosmetic then
			ShopService.GrantCosmetic(player, profile, tier.Premium.Cosmetic, "pass_premium")
		end
		granted = true
	end
	if not granted then
		return false, "Già riscosso"
	end
	ps().Sync(player, "Pass")
	ps().Sound(player, "Success")
	return true
end

-- ───────────────────────── Robux (opzionale) ─────────────────────────

local function productForCosmetic(cosmeticId)
	return Config.Monetization.CosmeticProducts[cosmeticId]
end

function ShopService.PromptPurchase(player, cosmeticId)
	cosmeticId = Guard.Str(cosmeticId, 48)
	local productId = cosmeticId and productForCosmetic(cosmeticId)
	if not productId or productId == 0 then
		return false, "Acquisto non disponibile"
	end
	local ok = pcall(function()
		MarketplaceService:PromptProductPurchase(player, productId)
	end)
	return ok
end

local function processReceipt(receipt)
	local player = Players:GetPlayerByUserId(receipt.PlayerId)
	if not player then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
	local profile = Registry.Get("DataService").WaitFor(player, 10)
	if not profile then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
	local ledgerId = "receipt:" .. receipt.PurchaseId
	if profile.Ledger[ledgerId] then
		return Enum.ProductPurchaseDecision.PurchaseGranted
	end
	for cosmeticId, productId in pairs(Config.Monetization.CosmeticProducts) do
		if productId == receipt.ProductId then
			ShopService.GrantCosmetic(player, profile, cosmeticId, "robux")
			profile.Ledger[ledgerId] = true
			Logger.Audit("Shop", player, "robux_purchase", cosmeticId)
			return Enum.ProductPurchaseDecision.PurchaseGranted
		end
	end
	return Enum.ProductPurchaseDecision.NotProcessedYet
end

local function checkGamePasses(player, profile)
	local M = Config.Monetization
	if M.FounderGamePassId ~= 0 and not profile.Founder then
		local ok, owns = pcall(MarketplaceService.UserOwnsGamePassAsync, MarketplaceService, player.UserId, M.FounderGamePassId)
		if ok and owns then
			profile.Founder = true
			for _, id in ipairs(Cosmetics.FounderBundle) do
				ShopService.GrantCosmetic(player, profile, id, "founder")
			end
			ps().Sync(player, "Founder")
		end
	end
	if M.CosmeticPassGamePassId ~= 0 and not profile.Pass.Premium then
		local ok, owns = pcall(MarketplaceService.UserOwnsGamePassAsync, MarketplaceService, player.UserId, M.CosmeticPassGamePassId)
		if ok and owns then
			profile.Pass.Premium = true
			ps().Sync(player, "Pass")
		end
	end
end

function ShopService.Init()
	Net.Function("BuyCosmetic").OnServerInvoke = ShopService.Buy
	Net.Function("EquipCosmetic").OnServerInvoke = ShopService.Equip
	Net.Function("ClaimPassTier").OnServerInvoke = ShopService.ClaimPassTier
	Net.Function("PromptPurchase").OnServerInvoke = ShopService.PromptPurchase
	Net.Event("Emote").OnServerEvent:Connect(function(player)
		local profile = Registry.Get("DataService").Get(player)
		if not profile then
			return
		end
		local emote = Cosmetics.Get(profile.Cosmetics.Equipped.emote)
		if emote and player.Character and player.Character.PrimaryPart then
			-- mostra a tutti un'emote non invasiva sopra la testa
			for _, other in ipairs(Players:GetPlayers()) do
				Net.Event("RaidEvent"):FireClient(other, "Emote", { UserId = player.UserId, Text = emote.Data.Text })
			end
		end
	end)
	MarketplaceService.ProcessReceipt = processReceipt
	MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(player, passId, purchased)
		if purchased then
			local profile = Registry.Get("DataService").Get(player)
			if profile then
				checkGamePasses(player, profile)
			end
		end
	end)
end

function ShopService.Start()
	EventBus.On("ProfileLoaded", function(player, profile)
		task.spawn(checkGamePasses, player, profile)
		player:SetAttribute("Trail", profile.Cosmetics.Equipped.trail)
		player:SetAttribute("Nameplate", profile.Cosmetics.Equipped.nameplate)
	end)
	EventBus.On("RaidCompleted", function(player, summary)
		if summary.Test then
			return
		end
		local profile = Registry.Get("DataService").Get(player)
		if profile then
			profile.Pass.Points += Cosmetics.Pass.PointsPerRaid
			ps().Sync(player, "Pass")
		end
	end)
end

return ShopService
