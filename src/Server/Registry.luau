--!nonstrict
-- Registro dei servizi: evita require circolari. I servizi si ottengono a runtime.
local Registry = { _services = {} }

function Registry.Register(name, service)
	Registry._services[name] = service
end

function Registry.Get(name)
	local s = Registry._services[name]
	assert(s, "Servizio non registrato: " .. tostring(name))
	return s
end

return Registry
