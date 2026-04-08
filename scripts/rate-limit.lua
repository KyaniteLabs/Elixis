-- Rate limiting middleware for SoulCraft
-- Can be used with OpenResty/Nginx for additional rate limiting layer

local _M = {}

-- Configuration
local DEFAULT_RATE = 10  -- requests per minute
local DEFAULT_BURST = 20
local CACHE_TTL = 60  -- seconds

-- Simple in-memory store (use Redis in production)
local store = {}

function _M.check_rate_limit(client_ip, path)
    local key = client_ip .. ":" .. path
    local now = ngx.time()

    -- Get or create entry
    local entry = store[key]
    if not entry or (now - entry.reset_at) > 60 then
        entry = {
            count = 0,
            reset_at = now + 60
        }
    end

    -- Check limit
    if entry.count >= DEFAULT_RATE then
        return false, "Rate limit exceeded. Try again in " .. (entry.reset_at - now) .. " seconds."
    end

    -- Increment and store
    entry.count = entry.count + 1
    store[key] = entry

    -- Set headers
    ngx.header["X-RateLimit-Limit"] = DEFAULT_RATE
    ngx.header["X-RateLimit-Remaining"] = math.max(0, DEFAULT_RATE - entry.count)
    ngx.header["X-RateLimit-Reset"] = entry.reset_at

    return true, nil
end

function _M.check_api_key()
    -- Optional: Add API key validation for sensitive endpoints
    local auth_header = ngx.var.http_authorization

    if not auth_header then
        return true  -- Allow if no auth required
    end

    -- Validate Bearer token if present
    local token = auth_header:match("^Bearer%s+(.+)$")
    if token then
        -- Add token validation logic here
        -- For now, just check it's non-empty
        if #token < 10 then
            return false, "Invalid API key"
        end
    end

    return true, nil
end

return _M
