--!nonstrict
-- Galleria dei vivai pubblicati: visita, «mi piace», codici layout.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Strings = require(Shared.Strings)
local Cosmetics = require(Shared.Catalog.Cosmetics)
local Format = require(Shared.Util.Format)
local Net = require(Shared.Util.Net)
local UI = require(script.Parent.UI)
local Toast = require(script.Parent.Toast)

local GalleryPanel = {}
local C = UI.Colors
local panel, body, header

local function render()
	body:ClearAllChildren()
	header:ClearAllChildren()
	local data = Net.Invoke("GetGallery")
	if type(data) ~= "table" then
		UI.Label(body, Strings.Error, { ZIndex = 13 })
		return
	end
	UI.Label(header, string.format(Strings.GalleryCode, data.MyCode) .. (data.Published and "" or "  ·  pubblica un layout per apparire in galleria"), { Font = UI.Theme.FontBold, TextSize = 14, Size = UDim2.new(0.6, 0, 1, 0), ZIndex = 13 })
	UI.Label(header, string.format("Ricompense di visita oggi: %d / %d", data.VisitsToday, data.VisitsMax), { TextSize = 14, TextColor3 = C.TextMuted, Size = UDim2.new(0.4, 0, 1, 0), Position = UDim2.fromScale(0.6, 0), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Right })
	local scroll = UI.Scroll(body)
	UI.Grid(scroll, UDim2.fromOffset(240, 190), 10)
	UI.Padding(scroll, 6)
	if #data.List == 0 then
		UI.Label(scroll, Strings.GalleryEmpty, { Size = UDim2.fromOffset(600, 60), ZIndex = 13 })
		return
	end
	for i, e in ipairs(data.List) do
		local skin = Cosmetics.Get(e.Skin or "skin_prato")
		local card = UI.Card(scroll, { Size = UDim2.fromOffset(240, 190), LayoutOrder = i })
		local swatch = UI.Frame(card, { Size = UDim2.new(1, 0, 0, 10), BackgroundColor3 = skin and skin.Data.Color or C.Success, ZIndex = 13 })
		UI.Corner(swatch, UI.Theme.Corner)
		UI.Label(card, (e.Online and "🟢 " or "") .. e.Name .. (e.IsMine and " (tu)" or ""), { Font = UI.Theme.Font, TextSize = 17, Size = UDim2.new(1, -16, 0, 24), Position = UDim2.fromOffset(8, 16), ZIndex = 13, TextTruncate = Enum.TextTruncate.AtEnd, TextWrapped = false })
		local plate = e.Nameplate and Cosmetics.Get(e.Nameplate)
		if plate and plate.Data.Text then
			UI.Pill(card, plate.Data.Text, plate.Data.Color or C.Info, { Position = UDim2.fromOffset(8, 42), Size = UDim2.fromOffset(100, 18) })
		end
		UI.Label(card, string.format("♥ %d   ·   difesa %s\n🐣 %d creature · 🛡 %d moduli", e.Likes, Format.Stars(e.Stars, 5), e.Creatures, e.Modules), { TextSize = 13, Size = UDim2.new(1, -16, 0, 44), Position = UDim2.fromOffset(8, 64), ZIndex = 13 })
		UI.Label(card, "Codice: " .. e.ShareCode, { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(1, -16, 0, 18), Position = UDim2.fromOffset(8, 108), ZIndex = 13 })
		if not e.IsMine then
			local v = UI.Button(card, "🚶 " .. Strings.GalleryVisit, function()
				local ok, msg = Net.Invoke("VisitVivaio", e.Key)
				if ok then
					panel:Close()
				else
					Toast.Show(msg or Strings.Error, "warning")
				end
			end, { Size = UDim2.new(0.5, -10, 0, 40), Position = UDim2.fromOffset(8, 138), Color = C.Info, TextSize = 14 })
			v.ZIndex = 13
			local l = UI.Button(card, e.LikedByMe and Strings.GalleryLiked or ("♡ " .. Strings.GalleryLike), function()
				local ok, msg = Net.Invoke("LikeVivaio", e.Key)
				if ok then
					render()
				else
					Toast.Show(msg or Strings.Error, "warning")
				end
			end, { Size = UDim2.new(0.5, -10, 0, 40), Position = UDim2.new(0.5, 2, 0, 138), Color = e.LikedByMe and C.TextMuted or C.Danger, TextSize = 14 })
			l.ZIndex = 13
		else
			UI.Label(card, "Il tuo vivaio", { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -16, 0, 40), Position = UDim2.fromOffset(8, 138), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
		end
	end
end

function GalleryPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "🖼 " .. Strings.GalleryTitle)
	header = UI.Frame(panel.Content, { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 26), ZIndex = 12 })
	body = UI.Frame(panel.Content, { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 1, -30), Position = UDim2.fromOffset(0, 30), ZIndex = 12 })
	panel.OnOpen = render
end

function GalleryPanel.Toggle()
	panel:Toggle()
end
function GalleryPanel.Open()
	panel:Open()
end
function GalleryPanel.Close()
	panel:Close()
end

return GalleryPanel
