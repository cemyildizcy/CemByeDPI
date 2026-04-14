"""
CemByeDPI - Evrensel Platform ve Domain Listesi
Bu listedeki platformların domainleri DPI aşımı (DoH ve Hosts) için kullanılır.
(Not: SNI fragmentation tüm 443 trafiğine evrensel etki eder).
"""

DOMAINS = {
    "Discord": [
        "discord.com",
        "www.discord.com",
        "cdn.discord.com",
        "media.discord.com",
        "images-ext-1.discordapp.net",
        "images-ext-2.discordapp.net",
        "discordapp.com",
        "www.discordapp.com",
        "gateway.discord.gg",
        "discord.gg",
        "discordapp.net",
        "discord.media",
        "discordcdn.com",
        "status.discord.com",
        "canary.discord.com",
        "ptb.discord.com",
        "media.discordapp.net",
        "images.discordapp.net",
        "cdn.discordapp.com",
    ],
    "Roblox": [
        "roblox.com",
        "www.roblox.com",
        "rbxcdn.com",
        "roblox.qq.com",
    ],
    "Wattpad": [
        "wattpad.com",
        "www.wattpad.com",
        "w.tt",
    ]
}

def get_combined_domains(platforms: list[str], custom_domains: list[str] = None) -> list[str]:
    """Seçilen platformların domainlerini ve varsa özel domainleri birleştirip döndürür."""
    combined = []
    for platform in platforms:
        if platform in DOMAINS:
            combined.extend(DOMAINS[platform])
            
    if custom_domains:
        for cd in custom_domains:
            cd = cd.strip()
            if cd and cd not in combined:
                combined.append(cd)
                
    return combined
