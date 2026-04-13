"""
CemByeDPI - Discord Domain Listesi
Discord'un tüm bilinen domain ve alt domainleri.
"""

DISCORD_DOMAINS = [
    "discord.com",
    "www.discord.com",
    "cdn.discord.com",
    "media.discord.com",
    "images-ext-1.discordapp.net",
    "images-ext-2.discordapp.net",
    "discordapp.com",
    "www.discordapp.com",
    "dl.discordapp.net",
    "gateway.discord.gg",
    "discord.gg",
    "discordapp.net",
    "discord.media",
    "discordcdn.com",
    "discord.dev",
    "discord.new",
    "discord.gift",
    "discordstatus.com",
    "dis.gd",
    "discord.co",
    "status.discord.com",
    "support.discord.com",
    "blog.discord.com",
    "canary.discord.com",
    "ptb.discord.com",
    "hammerandchisel.ssl.hwcdn.net",
    "media.discordapp.net",
    "images.discordapp.net",
    "cdn.discordapp.com",
    "updates.discord.com",
    "latency.discord.media",
    "router.discord.com",
]


def is_discord_domain(domain: str) -> bool:
    """Domain'in Discord'a ait olup olmadığını kontrol eder."""
    domain = domain.lower().strip(".")

    if domain in DISCORD_DOMAINS:
        return True

    for d in DISCORD_DOMAINS:
        if domain.endswith("." + d):
            return True

    return False
