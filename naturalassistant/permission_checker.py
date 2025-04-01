async def check_user_permission(member, allowed_roles):
    if member.guild_permissions.administrator:
        return True
    for role in member.roles:
        if role.id in allowed_roles:
            return True
    return False
