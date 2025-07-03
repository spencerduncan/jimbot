#!/bin/bash
# Retry helper script for CI pipeline
# Provides retry logic with exponential backoff

# Default values (can be overridden by environment variables)
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_DELAY="${RETRY_DELAY:-5}"

# Retry a command with exponential backoff
retry_command() {
    local command="$1"
    local description="${2:-command}"
    local max_attempts="${3:-$MAX_RETRIES}"
    local delay="${4:-$RETRY_DELAY}"
    
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        echo "[Retry] Attempting $description (attempt $attempt/$max_attempts)..."
        
        # Execute the command
        if eval "$command"; then
            echo "[Retry] ✅ $description succeeded"
            return 0
        fi
        
        # Check if we should retry
        if [ $attempt -lt $max_attempts ]; then
            echo "[Retry] ⚠️ $description failed, retrying in ${delay}s..."
            sleep $delay
            delay=$((delay * 2))  # Exponential backoff
        fi
        
        attempt=$((attempt + 1))
    done
    
    echo "[Retry] ❌ $description failed after $max_attempts attempts"
    return 1
}

# Retry with custom error handling
retry_with_fallback() {
    local primary_command="$1"
    local fallback_command="$2"
    local description="${3:-operation}"
    
    echo "[Retry] Attempting $description with fallback option..."
    
    if retry_command "$primary_command" "$description (primary)"; then
        return 0
    fi
    
    echo "[Retry] Primary method failed, trying fallback..."
    if eval "$fallback_command"; then
        echo "[Retry] ✅ $description succeeded with fallback"
        return 0
    fi
    
    echo "[Retry] ❌ Both primary and fallback methods failed for $description"
    return 1
}

# Check network connectivity with retry
check_network() {
    local sites=("github.com" "pypi.org" "registry.npmjs.org")
    local all_good=true
    
    echo "[Network] Checking connectivity..."
    
    for site in "${sites[@]}"; do
        if ! retry_command "curl -s --head --max-time 5 https://$site > /dev/null" "connectivity to $site" 2 2; then
            echo "[Network] ⚠️ Cannot reach $site"
            all_good=false
        fi
    done
    
    if [ "$all_good" = true ]; then
        echo "[Network] ✅ All sites reachable"
        return 0
    else
        echo "[Network] ⚠️ Some sites unreachable, CI may experience issues"
        return 1
    fi
}

# Download file with retry and fallback mirrors
download_with_retry() {
    local url="$1"
    local output="$2"
    local description="${3:-file}"
    
    # Try primary URL
    if retry_command "wget -q -O '$output' '$url'" "download $description"; then
        return 0
    fi
    
    # Try with curl as fallback
    if retry_command "curl -sL '$url' -o '$output'" "download $description with curl"; then
        return 0
    fi
    
    echo "[Download] ❌ Failed to download $description"
    return 1
}

# Install package with retry and error handling
install_package() {
    local package_manager="$1"
    local package="$2"
    local flags="${3:-}"
    
    case "$package_manager" in
        pip)
            retry_command "pip install $flags $package" "pip install $package"
            ;;
        apt)
            retry_command "sudo apt-get install -y $flags $package" "apt install $package"
            ;;
        npm)
            retry_command "npm install $flags $package" "npm install $package"
            ;;
        luarocks)
            retry_command "sudo luarocks install $flags $package" "luarocks install $package"
            ;;
        *)
            echo "[Install] Unknown package manager: $package_manager"
            return 1
            ;;
    esac
}

# Export functions for use in other scripts
export -f retry_command
export -f retry_with_fallback
export -f check_network
export -f download_with_retry
export -f install_package