#Requires -RunAsAdministrator
<#
.SYNOPSIS
Modifies the default network interface's gateway and DNS settings

.DESCRIPTION
1. Automatically detects the current default route interface
2. Supports switching from DHCP to static IP configuration (automatically records original information)
3. Modifies gateway and DNS settings
4. Outputs original configuration information for restoration

.PARAMETER ProxyGatewayIP
Specifies the IP address for the proxy gateway (used for both gateway and DNS)

.EXAMPLE
.\Set-ProxyGateway.ps1 -ProxyGatewayIP 192.168.1.1
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ [System.Net.IPAddress]::TryParse($_, [ref]$null) })]
    [string]$ProxyGatewayIP
)

# Initialize the record object
$Global:OriginalNetworkConfig = @{
    InterfaceIndex = $null
    DhcpEnabled    = $false
    IPAddress      = $null
    PrefixLength   = $null
    DefaultGateway = $null
    DNS            = $null
}

try {
    # Get the current default route
    $defaultRoute = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction Stop |
    Where-Object { $_.NextHop -ne $null } |
    Sort-Object RouteMetric |
    Select-Object -First 1

    if (-not $defaultRoute) {
        throw "Default route not found"
    }

    # Record interface information
    $interfaceIndex = $defaultRoute.InterfaceIndex
    $Global:OriginalNetworkConfig.InterfaceIndex = $interfaceIndex
    $Global:OriginalNetworkConfig.DefaultGateway = $defaultRoute.NextHop

    # Get interface configuration
    $interface = Get-NetIPInterface -InterfaceIndex $interfaceIndex -AddressFamily IPv4 -ErrorAction Stop
    $Global:OriginalNetworkConfig.DhcpEnabled = $interface.Dhcp -eq 'Enabled'

    # Get current IP configuration
    $ipConfig = Get-NetIPAddress -InterfaceIndex $interfaceIndex -AddressFamily IPv4 -ErrorAction Stop |
    Where-Object { $_.AddressState -eq 'Preferred' }

    if ($ipConfig) {
        $Global:OriginalNetworkConfig.IPAddress = $ipConfig.IPAddress
        $Global:OriginalNetworkConfig.PrefixLength = $ipConfig.PrefixLength
    }

    # Record current DNS settings
    $Global:OriginalNetworkConfig.DNS = (Get-DnsClientServerAddress -InterfaceIndex $interfaceIndex -AddressFamily IPv4).ServerAddresses

    # Handle DHCP to static
    if ($Global:OriginalNetworkConfig.DhcpEnabled) {
        Write-Host "Switching interface $interfaceIndex from DHCP to static configuration..."

        # Disable DHCP
        Set-NetIPInterface -InterfaceIndex $interfaceIndex -Dhcp Disabled -ErrorAction Stop

        # Remove automatically generated IP configuration
        Get-NetIPAddress -InterfaceIndex $interfaceIndex -AddressFamily IPv4 |
        Where-Object { $_.PrefixOrigin -eq 'Dhcp' } |
        Remove-NetIPAddress -Confirm:$false -ErrorAction Stop

        # Reapply static IP
        New-NetIPAddress -InterfaceIndex $interfaceIndex -IPAddress $Global:OriginalNetworkConfig.IPAddress `
            -PrefixLength $Global:OriginalNetworkConfig.PrefixLength -ErrorAction Stop | Out-Null
    }

    # Configure new gateway
    Write-Host "Updating default gateway..."
    Remove-NetRoute -InterfaceIndex $interfaceIndex -DestinationPrefix "0.0.0.0/0" -Confirm:$false -ErrorAction SilentlyContinue
    New-NetRoute -InterfaceIndex $interfaceIndex -DestinationPrefix "0.0.0.0/0" `
        -NextHop $ProxyGatewayIP -ErrorAction Stop | Out-Null

    # Configure DNS
    Write-Host "Updating DNS settings..."
    Set-DnsClientServerAddress -InterfaceIndex $interfaceIndex -ServerAddresses $ProxyGatewayIP -ErrorAction Stop

    # Clear DNS Client Cache
    Write-Host "Clear DNS Client Cache..."
    Clear-DnsClientCache -ErrorAction Stop

    # Display configuration summary
    Write-Host "`n=== New Configuration ==="
    Get-NetIPConfiguration -InterfaceIndex $interfaceIndex | Format-List
    Get-DnsClientServerAddress -InterfaceIndex $interfaceIndex -AddressFamily IPv4 | Format-List

    # Display original configuration
    Write-Host "`n=== Original Configuration (for restoration) ==="
    $Global:OriginalNetworkConfig | Format-List
}
catch {
    Write-Error "Configuration failed: $_"
    exit 1
}
