import discord
import subprocess
import asyncio
import json
from discord.ext import commands
import types

TOKEN = "token"  # Replace with your actual bot token
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# File to store user-container assignments
ASSIGNMENTS_FILE = "assigned_containers.json"
admin_role_id = 1351490436576968845  # Replace with actual Admin role ID

# Load assigned containers from file
def load_assignments():
    try:
        with open(ASSIGNMENTS_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save assigned containers to file
def save_assignments():
    with open(ASSIGNMENTS_FILE, "w") as file:
        json.dump(assigned_containers, file)

assigned_containers = load_assignments()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def assign(ctx, user: discord.User, container: str):
    """Assigns an LXD container to a user (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        assigned_containers[str(user.id)] = container
        save_assignments()
        await ctx.send(f"Assigned container `{container}` to {user.mention}")
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def optimize_node(ctx):
    """Optimizes the node by clearing cache and unnecessary data (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        try:
            subprocess.run(["sync"])
            subprocess.run(["echo", "3", ">", "/proc/sys/vm/drop_caches"], shell=True)
            subprocess.run(["docker", "system", "prune", "-af"])
            subprocess.run(["lxc", "exec", "--", "bash", "-c", "echo 1 > /proc/sys/vm/drop_caches"])
            await ctx.send("Node optimized: Cleared cache and pruned Docker containers.")
        except Exception as e:
            await ctx.send(f"An error occurred during node optimization: {str(e)}")
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def start(ctx):
    """Starts the assigned LXD container."""
    user_id = str(ctx.author.id)
    if user_id in assigned_containers:
        try:
            container = assigned_containers[user_id]
            subprocess.run(["lxc", "start", container])
            await ctx.send(f"Started container `{container}`.")
        except Exception as e:
            await ctx.send(f"Failed to start container `{container}`: {str(e)}")
    else:
        await ctx.send("You don't have an assigned container.")

@bot.command()
async def stop(ctx):
    """Stops the assigned LXD container."""
    user_id = str(ctx.author.id)
    if user_id in assigned_containers:
        try:
            container = assigned_containers[user_id]
            subprocess.run(["lxc", "stop", container])
            await ctx.send(f"Stopped container `{container}`.")
        except Exception as e:
            await ctx.send(f"Failed to stop container `{container}`: {str(e)}")
    else:
        await ctx.send("You don't have an assigned container.")

@bot.command()
async def restart(ctx):
    """Restarts the assigned LXD container."""
    user_id = str(ctx.author.id)
    if user_id in assigned_containers:
        try:
            container = assigned_containers[user_id]
            subprocess.run(["lxc", "restart", container])
            await ctx.send(f"Restarted container `{container}`.")
        except Exception as e:
            await ctx.send(f"Failed to restart container `{container}`: {str(e)}")
    else:
        await ctx.send("You don't have an assigned container.")

@bot.command()
async def list_containers(ctx):
    """Lists all available LXD containers (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        try:
            result = subprocess.run(["lxc", "list"], capture_output=True, text=True)
            await ctx.send(f"```{result.stdout}```")
        except Exception as e:
            await ctx.send(f"Failed to list containers: {str(e)}")
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def container_status(ctx):
    """Gets the status of the assigned LXD container."""
    user_id = str(ctx.author.id)
    if user_id in assigned_containers:
        try:
            container = assigned_containers[user_id]
            result = subprocess.run(["lxc", "info", container], capture_output=True, text=True)
            await ctx.send(f"```{result.stdout}```")
        except Exception as e:
            await ctx.send(f"Failed to get status for container `{container}`: {str(e)}")
    else:
        await ctx.send("You don't have an assigned container.")

@bot.command()
async def node_stats(ctx):
    """Fetches node system stats (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        try:
            cpu_usage = subprocess.run(["top", "-b", "-n", "1"], capture_output=True, text=True).stdout
            disk_usage = subprocess.run(["df", "-h"], capture_output=True, text=True).stdout
            memory_usage = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout
            await ctx.send(f"**CPU Usage:**\n```{cpu_usage.splitlines()[2]}```")
            await ctx.send(f"**Disk Usage:**\n```{disk_usage}```")
            await ctx.send(f"**Memory Usage:**\n```{memory_usage}```")
        except Exception as e:
            await ctx.send(f"Failed to fetch node stats: {str(e)}")
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def deploy_alpine(ctx, name: str, cpu_limit: int, memory_limit: str):
    """Deploys an Alpine container with specified CPU and memory limits (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        command = [
            "lxc", "launch", "my-alpine-ssh", name,
            "--config", f"limits.cpu={cpu_limit}",
            "--config", f"limits.memory={memory_limit}",
            "--config", f"limits.disk=3G"
        ]
        print(f"Executing command: {' '.join(command)}")  # Debugging statement
        result = await run_command_async(command)
        if result.returncode == 0:
            await ctx.send(f"Successfully deployed Alpine container `{name}` with {cpu_limit} CPUs and {memory_limit} memory.")
            await get_ssh_info(ctx, name, "alpine")
        else:
            error_message = f"Failed to deploy container:\n```{result.stderr}```"
            await ctx.send(error_message)
            print(f"Failed to deploy container {name}: {result.stderr}")  # Debugging statement
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def deploy_debian(ctx, name: str, cpu_limit: int, memory_limit: str):
    """Deploys a Debian container with specified CPU and memory limits (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        command = [
            "lxc", "launch", "my-debian-ssh", name,
            "--config", f"limits.cpu={cpu_limit}",
            "--config", f"limits.memory={memory_limit}",
            "--config", f"limits.disk=3G"
        ]
        print(f"Executing command: {' '.join(command)}")  # Debugging statement
        result = await run_command_async(command)
        if result.returncode == 0:
            await ctx.send(f"Successfully deployed Debian container `{name}` with {cpu_limit} CPUs and {memory_limit} memory.")
            await get_ssh_info(ctx, name, "debian")
        else:
            error_message = f"Failed to deploy container:\n```{result.stderr}```"
            await ctx.send(error_message)
            print(f"Failed to deploy container {name}: {result.stderr}")  # Debugging statement
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def delete_ct(ctx, name: str):
    """Deletes the specified LXD container (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        command = ["lxc", "delete", name, "--force"]
        print(f"Executing command: {' '.join(command)}")  # Debugging statement
        result = await run_command_async(command)
        if result.returncode == 0:
            await ctx.send(f"Successfully deleted container `{name}`.")
        else:
            error_message = f"Failed to delete container:\n```{result.stderr}```"
            await ctx.send(error_message)
            print(f"Failed to delete container {name}: {result.stderr}")  # Debugging statement
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def set_cpu_limit(ctx, name: str, cpu_limit: int):
    """Sets the CPU limit for the specified LXD container (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        command = ["lxc", "config", "set", name, f"limits.cpu={cpu_limit}"]
        print(f"Executing command: {' '.join(command)}")  # Debugging statement
        result = await run_command_async(command)
        if result.returncode == 0:
            await ctx.send(f"Successfully set CPU limit for container `{name}` to {cpu_limit}.")
        else:
            error_message = f"Failed to set CPU limit:\n```{result.stderr}```"
            await ctx.send(error_message)
            print(f"Failed to set CPU limit for container {name}: {result.stderr}")  # Debugging statement
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def set_memory_limit(ctx, name: str, memory_limit: str):
    """Sets the memory limit for the specified LXD container (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        command = ["lxc", "config", "set", name, f"limits.memory={memory_limit}"]
        print(f"Executing command: {' '.join(command)}")  # Debugging statement
        result = await run_command_async(command)
        if result.returncode == 0:
            await ctx.send(f"Successfully set memory limit for container `{name}` to {memory_limit}.")
        else:
            error_message = f"Failed to set memory limit:\n```{result.stderr}```"
            await ctx.send(error_message)
            print(f"Failed to set memory limit for container {name}: {result.stderr}")  # Debugging statement
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def get_config(ctx, name: str):
    """Gets the configuration for the specified LXD container (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        command = ["lxc", "config", "show", name]
        print(f"Executing command: {' '.join(command)}")  # Debugging statement
        result = await run_command_async(command)
        if result.returncode == 0:
            await ctx.send(f"Configuration for container `{name}`:\n```{result.stdout}```")
        else:
            error_message = f"Failed to get configuration:\n```{result.stderr}```"
            await ctx.send(error_message)
            print(f"Failed to get configuration for container {name}: {result.stderr}")  # Debugging statement
    else:
        await ctx.send("You do not have permission to use this command.")

async def run_command_async(command, timeout=None):
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return types.SimpleNamespace(returncode=process.returncode, stdout=stdout.decode(), stderr=stderr.decode())
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise

async def get_ssh_info(ctx, container: str, container_type: str):
    """Gets the SSH connection string for the container."""
    try:
        # Get container IP address
        result = await run_command_async(["lxc", "list", container, "--format=json"])
        if result.returncode != 0:
            await ctx.send(f"Failed to get container info for `{container}`:\n```{result.stderr}```")
            return
        container_info = json.loads(result.stdout)[0]
        container_ip = container_info["state"]["network"]["eth0"]["addresses"][0]["address"]

        # Get SSH port
        ssh_port = 22  # Default SSH port

        # Get SSH username
        ssh_user = "myuser"

        # Construct SSH connection string
        ssh_command = f"ssh {ssh_user}@{container_ip} -p {ssh_port}"

        # Send SSH connection string to user
        await ctx.author.send(embed=discord.Embed(description=f"### Successfully created Instance\nSSH Command:\n{ssh_command}\nOS: {container_type.capitalize()}", color=0x00ff00))
        await ctx.send(f"SSH connection string for container `{container}`. Check your DMs for details.")
    except Exception as e:
        await ctx.send(f"An error occurred while getting SSH info for container `{container}`: {str(e)}")

@bot.command()
async def notify_restart(ctx):
    """Notifies all customers that the main VM has restarted (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        for user_id, container in assigned_containers.items():
            user = await bot.fetch_user(int(user_id))
            if user:
                await user.send(embed=discord.Embed(description="The main VM has restarted. You will receive your new tmate SSH link shortly.", color=0xffa500))
        await ctx.send("All customers have been notified.")
    else:
        await ctx.send("You do not have permission to use this command.")

@bot.command()
async def tmate(ctx, container: str, *, tmate_link: str):
    """Sends a tmate SSH link to a specific customer (Admin only)."""
    if admin_role_id in [role.id for role in ctx.author.roles]:
        user_id = None
        for u_id, c_name in assigned_containers.items():
            if c_name == container:
                user_id = u_id
                break
        if user_id:
            user = await bot.fetch_user(int(user_id))
            if user:
                await user.send(embed=discord.Embed(description=f"### New tmate SSH Link\nSSH Command:\n{tmate_link}", color=0x00ff00))
                await ctx.send(f"Sent tmate SSH link to {user.mention} for container `{container}`.")
            else:
                await ctx.send(f"Failed to find user for container `{container}`.")
        else:
            await ctx.send(f"No container found with the name `{container}`.")
    else:
        await ctx.send("You do not have permission to use this command.")
