--!nonstrict
-- Token bucket per giocatore e per azione. Impedisce spam dei remoti (sezione 8 GDD).
local RateLimiter = {}
RateLimiter.__index = RateLimiter

function RateLimiter.new(capacity, refillPerSecond)
	return setmetatable({ _cap = capacity, _refill = refillPerSecond, _buckets = {} }, RateLimiter)
end

function RateLimiter:Allow(key, cost)
	cost = cost or 1
	local now = os.clock()
	local b = self._buckets[key]
	if not b then
		b = { tokens = self._cap, last = now }
		self._buckets[key] = b
	end
	b.tokens = math.min(self._cap, b.tokens + (now - b.last) * self._refill)
	b.last = now
	if b.tokens >= cost then
		b.tokens -= cost
		return true
	end
	return false
end

function RateLimiter:Clear(key)
	self._buckets[key] = nil
end

return RateLimiter
