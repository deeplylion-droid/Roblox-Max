--!nonstrict
-- Bottega dello stile: cosmetici con gettoni (e Robux opzionali), Pass delle Nuvole trasparente.
local MarketplaceService = game:GetService("MarketplaceService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Cosmetics = require(Shared.Catalog.Cosmetics)
local Net = require(Shared.Util.Net)
local UI = require(script.Parent.UI)
local Toast = require(script.Parent.Toast)
local State = require(script.Parent.Parent.Controllers.State)

local ShopPanel = {}
local C = UI.Colors
local panel, tabs, body, tokensLabel
local current = "skin"
local priceCache = {}

local function robuxPrice(productId)
	if priceCache[productId] ~= nil then
		return priceCache[productId]
	end
	local ok, info = pcall(function()
		return MarketplaceService:GetProductInfo(productId, Enum.InfoType.Product)
	end)
	priceCache[productId] = ok and info and info.PriceInRobux or false
	return priceCache[productId]
end

local function renderSlot(slot)
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.Grid(scroll, UDim2.fromOffset(220, 170), 10)
	UI.Padding(scroll, 6)
	local cos = State.Get("Cosmetics") or { Owned = {}, Equipped = {} }
	local tokens = State.Get("StyleTokens") or 0
	local order = 0
	for _, c in ipairs(Cosmetics.List) do
		if c.Slot == slot then
			order += 1
			local owned = cos.Owned[c.Id] == true
			local equipped = cos.Equipped[slot] == c.Id
			local card = UI.Card(scroll, { Size = UDim2.fromOffset(220, 170), LayoutOrder = order, BackgroundColor3 = equipped and Color3.fromRGB(225, 245, 235) or C.PanelAlt })
			local swatchColor = c.Data.Color or c.Data.Tint or c.Data.Trim or C.Info
			local sw = UI.Frame(card, { Size = UDim2.fromOffset(44, 44), Position = UDim2.fromOffset(10, 10), BackgroundColor3 = swatchColor, ZIndex = 13 })
			UI.Corner(sw, UDim.new(1, 0))
			if c.Data.Text then
				UI.Label(sw, c.Data.Text, { Size = UDim2.fromScale(1, 1), TextSize = 20, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 14 })
			end
			UI.Label(card, c.Name, { Font = UI.Theme.Font, TextSize = 16, Size = UDim2.new(1, -70, 0, 24), Position = UDim2.fromOffset(62, 10), ZIndex = 13 })
			UI.Label(card, c.Description, { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(1, -70, 0, 40), Position = UDim2.fromOffset(62, 34), ZIndex = 13, TextYAlignment = Enum.TextYAlignment.Top })
			local y = 118
			if owned then
				local b = UI.Button(card, equipped and ("✔ " .. Strings.ShopEquipped) or Strings.ShopEquip, function()
					if not equipped then
						Net.Invoke("EquipCosmetic", c.Id)
					end
				end, { Size = UDim2.new(1, -20, 0, 40), Position = UDim2.fromOffset(10, y), Color = equipped and C.TextMuted or C.Success, TextSize = 14 })
				b.ZIndex = 13
			else
				local productId = Config.Monetization.CosmeticProducts[c.Id]
				local hasRobux = productId and productId ~= 0
				if c.TokenPrice then
					local b = UI.Button(card, string.format("🎨 " .. Strings.ShopBuyTokens, c.TokenPrice), function()
						local ok, msg = Net.Invoke("BuyCosmetic", c.Id)
						if not ok then
							Toast.Show(msg or Strings.Error, "warning")
						end
					end, { Size = UDim2.new(hasRobux and 0.5 or 1, -(hasRobux and 14 or 20), 0, 40), Position = UDim2.fromOffset(10, y), Color = tokens >= c.TokenPrice and C.Token or C.TextMuted, TextSize = 13 })
					b.ZIndex = 13
				else
					local src = ({ pass = "Pass delle Nuvole", founder = "Bundle fondatore", weekly = "Sfida settimanale", album = "Traguardo album" })[c.Source] or "Non in vendita"
					UI.Label(card, "Da: " .. src, { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(hasRobux and 0.5 or 1, -20, 0, 40), Position = UDim2.fromOffset(10, y), ZIndex = 13 })
				end
				if hasRobux then
					local price = robuxPrice(productId)
					local b = UI.Button(card, price and ("R$ " .. price) or Strings.ShopBuyRobux, function()
						Net.Invoke("PromptPurchase", c.Id)
					end, { Size = UDim2.new(0.5, -14, 0, 40), Position = UDim2.new(0.5, 4, 0, y), Color = C.Success, TextSize = 13 })
					b.ZIndex = 13
				end
			end
		end
	end
end

local function renderPass()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.List(scroll, Enum.FillDirection.Vertical, 8)
	UI.Padding(scroll, 6)
	local pass = State.Get("Pass") or { Points = 0, ClaimedFree = {}, ClaimedPremium = {}, Premium = false }
	UI.Label(scroll, Strings.ShopPassTitle .. string.format("  ·  %d punti", pass.Points), { Font = UI.Theme.Font, TextSize = 20, Size = UDim2.new(1, 0, 0, 28), LayoutOrder = 0, ZIndex = 13 })
	UI.Label(scroll, Strings.ShopPassNote .. ". Punti: +10 per commissione, +4 per incursione, +15 per traguardo album. Nessuna scadenza.", { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 40), LayoutOrder = 1, ZIndex = 13 })
	if not pass.Premium then
		local id = Config.Monetization.CosmeticPassGamePassId
		local b = UI.Button(scroll, id ~= 0 and "Sblocca la corsia Premium (solo estetica)" or "Corsia Premium: non disponibile in questa build", function()
			if id ~= 0 then
				pcall(function()
					MarketplaceService:PromptGamePassPurchase(game:GetService("Players").LocalPlayer, id)
				end)
			end
		end, { Size = UDim2.new(1, -8, 0, 44), LayoutOrder = 2, Color = id ~= 0 and C.Token or C.TextMuted, TextSize = 14 })
		b.ZIndex = 13
	end
	local function describe(r)
		if r.Tokens then
			return "🎨 " .. r.Tokens .. " gettoni"
		end
		if r.Cosmetic then
			local c = Cosmetics.Get(r.Cosmetic)
			return "✨ " .. (c and c.Name or r.Cosmetic)
		end
		return "—"
	end
	for i, tier in ipairs(Cosmetics.Pass.Tiers) do
		local reached = pass.Points >= tier.Points
		local freeClaimed = pass.ClaimedFree[tostring(i)] == true
		local premClaimed = pass.ClaimedPremium[tostring(i)] == true
		local card = UI.Card(scroll, { Size = UDim2.new(1, -8, 0, 70), LayoutOrder = 10 + i, BackgroundColor3 = reached and C.PanelAlt or Color3.fromRGB(225, 230, 240) })
		UI.Label(card, string.format("Livello %d · %d punti", i, tier.Points), { Font = UI.Theme.FontBold, TextSize = 15, Size = UDim2.fromOffset(170, 30), Position = UDim2.fromOffset(12, 6), ZIndex = 13 })
		UI.Label(card, "Gratis: " .. describe(tier.Free) .. (freeClaimed and " ✔" or ""), { TextSize = 13, Size = UDim2.fromOffset(260, 24), Position = UDim2.fromOffset(12, 36), ZIndex = 13 })
		UI.Label(card, "Premium: " .. describe(tier.Premium) .. (premClaimed and " ✔" or ""), { TextSize = 13, TextColor3 = C.Token, Size = UDim2.fromOffset(260, 24), Position = UDim2.fromOffset(290, 36), ZIndex = 13 })
		local claimable = reached and (not freeClaimed or (pass.Premium and not premClaimed))
		local b = UI.Button(card, claimable and "🎁 Riscuoti" or (reached and "✔ Riscosso" or "Bloccato"), function()
			if claimable then
				local ok, msg = Net.Invoke("ClaimPassTier", i)
				if not ok then
					Toast.Show(msg or Strings.Error, "warning")
				end
			end
		end, { Size = UDim2.fromOffset(150, 40), Position = UDim2.new(1, -162, 0.5, -20), Color = claimable and C.Success or C.TextMuted, TextSize = 14 })
		b.ZIndex = 13
	end
end

function ShopPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "🛍 " .. Strings.ShopTitle)
	tokensLabel = UI.Label(panel.Content, "", { Font = UI.Theme.FontBold, TextSize = 15, Size = UDim2.new(1, 0, 0, 22), ZIndex = 13 })
	tabs = UI.Tabs(panel.Content, {
		{ Id = "skin", Label = "🏝 Skin" }, { Id = "sky", Label = "🌅 Cieli" }, { Id = "trail", Label = "✨ Scie" }, { Id = "emote", Label = "🙂 Emote" }, { Id = "nameplate", Label = "🏷 Targhette" }, { Id = "pass", Label = "🎫 Pass" },
	}, function(name)
		current = name
		if name == "pass" then
			renderPass()
		else
			renderSlot(name)
		end
	end, { Position = UDim2.fromOffset(0, 26) })
	body = UI.Frame(panel.Content, { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 1, -104), Position = UDim2.fromOffset(0, 80), ZIndex = 12 })
	UI.Label(panel.Content, Strings.ShopEthics, { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 22), Position = UDim2.new(0, 0, 1, -22), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
	panel.OnOpen = function()
		tokensLabel.Text = string.format(Strings.ShopTokens, State.Get("StyleTokens") or 0) .. "  ·  i gettoni si guadagnano con commissioni, album e maestria"
		tabs:Select(current)
	end
	State.Changed:Connect(function(key)
		if panel.IsOpen and (key == "Cosmetics" or key == "StyleTokens" or key == "Pass") then
			tokensLabel.Text = string.format(Strings.ShopTokens, State.Get("StyleTokens") or 0)
			tabs:Select(current)
		end
	end)
end

function ShopPanel.Toggle()
	panel:Toggle()
end
function ShopPanel.Open()
	panel:Open()
end
function ShopPanel.Close()
	panel:Close()
end

return ShopPanel
