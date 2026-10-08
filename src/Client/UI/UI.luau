--!nonstrict
--[[
	UI: costruttore di interfaccia con tema coerente. Pulsanti grandi, testo leggibile,
	indicazioni testuali oltre ai colori (accessibilità), animazioni leggere.
]]
local TweenService = game:GetService("TweenService")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Theme = require(ReplicatedStorage.Shared.Theme)

local UI = {}
local C = Theme.Colors

local function apply(inst, props)
	for k, v in pairs(props or {}) do
		inst[k] = v
	end
	return inst
end

function UI.Corner(parent, radius)
	local c = Instance.new("UICorner")
	c.CornerRadius = radius or Theme.Corner
	c.Parent = parent
	return c
end

function UI.Stroke(parent, color, thickness, transparency)
	local s = Instance.new("UIStroke")
	s.Color = color or C.Stroke
	s.Thickness = thickness or Theme.StrokeThickness
	s.Transparency = transparency or 0
	s.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	s.Parent = parent
	return s
end

function UI.Padding(parent, all, h, v)
	local p = Instance.new("UIPadding")
	local ph = UDim.new(0, h or all or 8)
	local pv = UDim.new(0, v or all or 8)
	p.PaddingLeft, p.PaddingRight, p.PaddingTop, p.PaddingBottom = ph, ph, pv, pv
	p.Parent = parent
	return p
end

function UI.List(parent, direction, padding, align)
	local l = Instance.new("UIListLayout")
	l.FillDirection = direction or Enum.FillDirection.Vertical
	l.Padding = UDim.new(0, padding or 8)
	l.SortOrder = Enum.SortOrder.LayoutOrder
	l.HorizontalAlignment = align or Enum.HorizontalAlignment.Left
	l.Parent = parent
	return l
end

function UI.Grid(parent, cellSize, padding)
	local g = Instance.new("UIGridLayout")
	g.CellSize = cellSize or UDim2.fromOffset(150, 190)
	g.CellPadding = UDim2.fromOffset(padding or 10, padding or 10)
	g.SortOrder = Enum.SortOrder.LayoutOrder
	g.Parent = parent
	return g
end

function UI.Gradient(parent, c1, c2, rotation)
	local g = Instance.new("UIGradient")
	g.Color = ColorSequence.new(c1, c2)
	g.Rotation = rotation or 90
	g.Parent = parent
	return g
end

function UI.Frame(parent, props)
	local f = Instance.new("Frame")
	f.BackgroundColor3 = C.Panel
	f.BorderSizePixel = 0
	f.Size = UDim2.fromScale(1, 1)
	apply(f, props)
	f.Parent = parent
	return f
end

function UI.Label(parent, text, props)
	local l = Instance.new("TextLabel")
	l.BackgroundTransparency = 1
	l.Font = Theme.FontBody
	l.TextColor3 = C.Text
	l.TextSize = Theme.TextSize.Body
	l.TextXAlignment = Enum.TextXAlignment.Left
	l.TextWrapped = true
	l.RichText = true
	l.Size = UDim2.new(1, 0, 0, 24)
	l.Text = text or ""
	apply(l, props)
	l.Parent = parent
	return l
end

function UI.Title(parent, text, props)
	return UI.Label(parent, text, apply({ Font = Theme.Font, TextSize = Theme.TextSize.Header, Size = UDim2.new(1, 0, 0, 32) }, props))
end

-- Pulsante grande con stato hover/pressed. onClick riceve il pulsante.
function UI.Button(parent, text, onClick, props)
	props = props or {}
	local b = Instance.new("TextButton")
	b.AutoButtonColor = false
	b.BackgroundColor3 = props.Color or C.Info
	b.BorderSizePixel = 0
	b.Font = Theme.Font
	b.TextColor3 = props.TextColor or C.TextOnDark
	b.TextSize = props.TextSize or Theme.TextSize.Body
	b.TextWrapped = true
	b.Size = props.Size or UDim2.new(1, 0, 0, Theme.ButtonHeight)
	b.Text = text
	b.LayoutOrder = props.LayoutOrder or 0
	b.Position = props.Position or UDim2.new()
	b.AnchorPoint = props.AnchorPoint or Vector2.new()
	b.Visible = props.Visible ~= false
	b.Name = props.Name or "Button"
	UI.Corner(b, props.Corner or Theme.Corner)
	UI.Stroke(b, Color3.new(1, 1, 1), 1.5, 0.75)
	local base = b.BackgroundColor3
	local function tint(f)
		return Color3.new(math.clamp(base.R * f, 0, 1), math.clamp(base.G * f, 0, 1), math.clamp(base.B * f, 0, 1))
	end
	b.MouseEnter:Connect(function()
		TweenService:Create(b, TweenInfo.new(0.12), { BackgroundColor3 = tint(1.08) }):Play()
	end)
	b.MouseLeave:Connect(function()
		TweenService:Create(b, TweenInfo.new(0.12), { BackgroundColor3 = base }):Play()
	end)
	b.MouseButton1Down:Connect(function()
		TweenService:Create(b, TweenInfo.new(0.08), { BackgroundColor3 = tint(0.9) }):Play()
	end)
	b.MouseButton1Up:Connect(function()
		TweenService:Create(b, TweenInfo.new(0.08), { BackgroundColor3 = base }):Play()
	end)
	if onClick then
		b.Activated:Connect(function()
			onClick(b)
		end)
	end
	b.Parent = parent
	-- permette di cambiare colore base da fuori
	b:SetAttribute("BaseColor", base)
	b:GetAttributeChangedSignal("BaseColor"):Connect(function()
		base = b:GetAttribute("BaseColor")
		b.BackgroundColor3 = base
	end)
	return b
end

function UI.SetButtonColor(b, color)
	b:SetAttribute("BaseColor", color)
end

function UI.SetEnabled(b, enabled)
	b.Active = enabled
	b.AutoButtonColor = false
	b.TextTransparency = enabled and 0 or 0.45
	b.BackgroundTransparency = enabled and 0 or 0.4
end

-- Pannello modale centrato con titolo e pulsante chiudi. Ritorna (panel, content)
function UI.Panel(parent, title, size)
	local overlay = UI.Frame(parent, { Name = "Overlay_" .. title, BackgroundColor3 = Color3.fromRGB(20, 30, 60), BackgroundTransparency = 0.45, Visible = false, ZIndex = 10 })
	local panel = UI.Frame(overlay, { Name = "Panel", Size = size or UDim2.new(0.86, 0, 0.84, 0), Position = UDim2.fromScale(0.5, 0.5), AnchorPoint = Vector2.new(0.5, 0.5), ZIndex = 11 })
	UI.Corner(panel, UDim.new(0, 20))
	UI.Stroke(panel, C.Stroke, 3)
	local sizeConstraint = Instance.new("UISizeConstraint")
	sizeConstraint.MaxSize = Vector2.new(1100, 720)
	sizeConstraint.Parent = panel
	local header = UI.Frame(panel, { Name = "Header", Size = UDim2.new(1, 0, 0, 56), BackgroundColor3 = C.PanelAlt, ZIndex = 12 })
	UI.Corner(header, UDim.new(0, 20))
	local headerFix = UI.Frame(header, { Size = UDim2.new(1, 0, 0.5, 0), Position = UDim2.fromScale(0, 0.5), BackgroundColor3 = C.PanelAlt, ZIndex = 12 })
	UI.Label(header, title, { Font = Theme.Font, TextSize = Theme.TextSize.Title, Size = UDim2.new(1, -140, 1, 0), Position = UDim2.fromOffset(20, 0), ZIndex = 13 })
	local close = UI.Button(header, "✕", nil, { Size = UDim2.fromOffset(44, 44), Position = UDim2.new(1, -52, 0.5, -22), Color = C.Danger, Name = "Close", Corner = UDim.new(0, 12) })
	close.ZIndex = 13
	local content = UI.Frame(panel, { Name = "Content", Size = UDim2.new(1, -24, 1, -72), Position = UDim2.fromOffset(12, 64), BackgroundTransparency = 1, ZIndex = 12 })
	local api = { Overlay = overlay, Panel = panel, Content = content, CloseButton = close, Header = header, IsOpen = false }
	function api:Open()
		if self.IsOpen then
			return
		end
		self.IsOpen = true
		overlay.Visible = true
		panel.Size = UDim2.new((size or UDim2.new(0.86, 0, 0.84, 0)).X.Scale * 0.92, 0, (size or UDim2.new(0.86, 0, 0.84, 0)).Y.Scale * 0.92, 0)
		overlay.BackgroundTransparency = 1
		TweenService:Create(overlay, TweenInfo.new(0.18), { BackgroundTransparency = 0.45 }):Play()
		TweenService:Create(panel, TweenInfo.new(0.22, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Size = size or UDim2.new(0.86, 0, 0.84, 0) }):Play()
		if self.OnOpen then
			self.OnOpen()
		end
	end
	function api:Close()
		if not self.IsOpen then
			return
		end
		self.IsOpen = false
		overlay.Visible = false
		if self.OnClose then
			self.OnClose()
		end
	end
	function api:Toggle()
		if self.IsOpen then
			self:Close()
		else
			self:Open()
		end
	end
	close.Activated:Connect(function()
		api:Close()
	end)
	-- click sullo sfondo chiude
	local bgButton = Instance.new("TextButton")
	bgButton.BackgroundTransparency = 1
	bgButton.Text = ""
	bgButton.Size = UDim2.fromScale(1, 1)
	bgButton.ZIndex = 10
	bgButton.Parent = overlay
	bgButton.Activated:Connect(function()
		api:Close()
	end)
	headerFix.ZIndex = 12
	return api
end

function UI.Scroll(parent, props)
	local s = Instance.new("ScrollingFrame")
	s.BackgroundTransparency = 1
	s.BorderSizePixel = 0
	s.Size = UDim2.fromScale(1, 1)
	s.CanvasSize = UDim2.new()
	s.AutomaticCanvasSize = Enum.AutomaticSize.Y
	s.ScrollBarThickness = 8
	s.ScrollBarImageColor3 = C.Stroke
	s.ScrollingDirection = Enum.ScrollingDirection.Y
	s.ZIndex = 12
	apply(s, props)
	s.Parent = parent
	return s
end

-- Card con bordo e sfondo
function UI.Card(parent, props)
	local f = UI.Frame(parent, apply({ BackgroundColor3 = C.PanelAlt, Size = UDim2.new(1, 0, 0, 90), ZIndex = 12 }, props))
	UI.Corner(f, Theme.Corner)
	UI.Stroke(f, C.Stroke, 1.5, 0.5)
	return f
end

-- Barra di progresso con etichetta testuale
function UI.Progress(parent, props)
	local bg = UI.Frame(parent, apply({ BackgroundColor3 = Color3.fromRGB(210, 222, 240), Size = UDim2.new(1, 0, 0, 18), ZIndex = 12 }, props))
	UI.Corner(bg, UDim.new(1, 0))
	local fill = UI.Frame(bg, { Name = "Fill", BackgroundColor3 = (props and props.FillColor) or C.Success, Size = UDim2.fromScale(0, 1), ZIndex = 13 })
	UI.Corner(fill, UDim.new(1, 0))
	local label = UI.Label(bg, "", { Font = Theme.FontBold, TextSize = 13, TextXAlignment = Enum.TextXAlignment.Center, Size = UDim2.fromScale(1, 1), ZIndex = 14, TextColor3 = C.Text })
	local api = { Frame = bg }
	function api:Set(value, max, text)
		local frac = max > 0 and math.clamp(value / max, 0, 1) or 0
		TweenService:Create(fill, TweenInfo.new(0.25), { Size = UDim2.fromScale(frac, 1) }):Play()
		label.Text = text or string.format("%d / %d", value, max)
	end
	return api
end

-- Interruttore con testo "Attivo/Spento" (accessibilità: non solo colore)
function UI.Toggle(parent, text, initial, onChange, layoutOrder)
	local row = UI.Frame(parent, { BackgroundColor3 = C.PanelAlt, Size = UDim2.new(1, 0, 0, 56), ZIndex = 12, LayoutOrder = layoutOrder or 0 })
	UI.Corner(row)
	UI.Label(row, text, { Size = UDim2.new(1, -150, 1, 0), Position = UDim2.fromOffset(14, 0), ZIndex = 13 })
	local value = initial == true
	local btn
	local function render()
		btn.Text = value and "● Attivo" or "○ Spento"
		UI.SetButtonColor(btn, value and C.Success or C.TextMuted)
	end
	btn = UI.Button(row, "", function()
		value = not value
		render()
		onChange(value)
	end, { Size = UDim2.fromOffset(120, 40), Position = UDim2.new(1, -132, 0.5, -20), Color = C.Success })
	btn.ZIndex = 13
	render()
	local api = { Row = row }
	function api:Set(v)
		value = v == true
		render()
	end
	return api
end

-- Anteprima 3D di un modello in un ViewportFrame (ruota lentamente)
local viewports = {}
function UI.Viewport(parent, model, props)
	local vp = Instance.new("ViewportFrame")
	vp.BackgroundColor3 = (props and props.BackgroundColor3) or Color3.fromRGB(222, 236, 255)
	vp.BackgroundTransparency = (props and props.BackgroundTransparency) or 0
	vp.BorderSizePixel = 0
	vp.Size = (props and props.Size) or UDim2.fromScale(1, 1)
	vp.Position = (props and props.Position) or UDim2.new()
	vp.Ambient = Color3.fromRGB(180, 190, 220)
	vp.LightColor = Color3.fromRGB(255, 250, 240)
	vp.LightDirection = Vector3.new(-1, -2, -1)
	vp.ZIndex = (props and props.ZIndex) or 13
	UI.Corner(vp, Theme.CornerSmall)
	local cam = Instance.new("Camera")
	cam.Parent = vp
	vp.CurrentCamera = cam
	local world = Instance.new("WorldModel")
	world.Parent = vp
	if model then
		model.Parent = world
		local cf, size = model:GetBoundingBox()
		local radius = math.max(size.X, size.Y, size.Z) * ((props and props.Zoom) or 1.15) + 1
		local entry = { Camera = cam, Center = cf.Position, Radius = radius, Angle = math.random() * math.pi * 2, Frame = vp }
		table.insert(viewports, entry)
		cam.CFrame = CFrame.lookAt(entry.Center + Vector3.new(math.cos(entry.Angle) * radius, radius * 0.45, math.sin(entry.Angle) * radius), entry.Center)
	end
	vp.Parent = parent
	return vp
end

RunService.RenderStepped:Connect(function(dt)
	for i = #viewports, 1, -1 do
		local v = viewports[i]
		if not v.Frame.Parent then
			table.remove(viewports, i)
		elseif v.Frame.Visible and v.Frame.AbsoluteSize.X > 0 then
			v.Angle += dt * 0.6
			v.Camera.CFrame = CFrame.lookAt(v.Center + Vector3.new(math.cos(v.Angle) * v.Radius, v.Radius * 0.45, math.sin(v.Angle) * v.Radius), v.Center)
		end
	end
end)

-- Testo con "pillola" colorata (es. rarità) — colore + testo
function UI.Pill(parent, text, color, props)
	local f = UI.Frame(parent, apply({ BackgroundColor3 = color, Size = UDim2.fromOffset(90, 22), ZIndex = 13 }, props))
	UI.Corner(f, UDim.new(1, 0))
	UI.Label(f, text, { Font = Theme.FontBold, TextSize = 12, TextColor3 = Color3.new(1, 1, 1), TextXAlignment = Enum.TextXAlignment.Center, Size = UDim2.fromScale(1, 1), ZIndex = 14 })
	return f
end

function UI.TextBox(parent, placeholder, props)
	local t = Instance.new("TextBox")
	t.BackgroundColor3 = Color3.new(1, 1, 1)
	t.BorderSizePixel = 0
	t.Font = Theme.FontBody
	t.TextSize = Theme.TextSize.Body
	t.TextColor3 = C.Text
	t.PlaceholderText = placeholder or ""
	t.PlaceholderColor3 = C.TextMuted
	t.Text = ""
	t.ClearTextOnFocus = false
	t.Size = UDim2.new(1, 0, 0, 44)
	t.ZIndex = 13
	apply(t, props)
	UI.Corner(t, Theme.CornerSmall)
	UI.Stroke(t, C.Stroke, 1.5)
	t.Parent = parent
	return t
end

-- Tab bar: ritorna api:Select(name); onSelect(name)
function UI.Tabs(parent, names, onSelect, props)
	local bar = UI.Frame(parent, apply({ BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 46), ZIndex = 12 }, props))
	UI.List(bar, Enum.FillDirection.Horizontal, 8)
	local buttons = {}
	local api = {}
	function api:Select(name)
		for n, b in pairs(buttons) do
			UI.SetButtonColor(b, n == name and C.Info or C.TextMuted)
		end
		onSelect(name)
	end
	for i, n in ipairs(names) do
		local label = type(n) == "table" and n.Label or n
		local id = type(n) == "table" and n.Id or n
		buttons[id] = UI.Button(bar, label, function()
			api:Select(id)
		end, { Size = UDim2.new(1 / #names, -8, 1, 0), Color = C.TextMuted, LayoutOrder = i, TextSize = 16 })
		buttons[id].ZIndex = 13
	end
	return api
end

UI.Colors = C
UI.Theme = Theme
return UI
