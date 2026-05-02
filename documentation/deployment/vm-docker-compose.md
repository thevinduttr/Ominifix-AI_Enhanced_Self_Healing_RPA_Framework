# Azure VM Docker Compose CI/CD Deployment

This project is best deployed to Azure first with one Ubuntu VM and Docker Compose. That matches the current architecture: one root `docker-compose.yml`, multiple Dockerfiles, FastAPI services, React/Vite dashboards, RabbitMQ, and RPA bot containers.

The CI/CD flow is:

```text
Push to deployment_1
  -> GitHub Actions
  -> Validate docker-compose.yml
  -> SSH into Azure VM
  -> Pull latest deployment_1 branch
  -> Rebuild and restart Docker Compose services
```

## 1. Create an Azure Ubuntu VM

In Azure Portal, create a Linux virtual machine.

Recommended starting size:

```text
Demo or university project: Standard B2s or B2ms
More stable staging setup: Standard D2s_v5
```

Use Ubuntu LTS, SSH key authentication, and create or select a resource group for the project.

Why: This repo already runs as a multi-container Docker Compose application. A single VM is the simplest Azure deployment target because it can run the current Compose stack without redesigning the project for Kubernetes or Azure Container Apps.

## 2. Configure Azure networking

In the VM Network Security Group, allow SSH:

```text
22/tcp
```

For a demo deployment, only open the application ports you need, for example:

```text
3000/tcp   frontend_monitor
5173/tcp   ai_element_locator_dashboard
8501/tcp   ai_rpa_healing_engine API
8601/tcp   ai_rpa_healing_ui
```

Do not publicly open RabbitMQ:

```text
5672/tcp
15672/tcp
```

Why: Azure blocks inbound traffic unless the Network Security Group allows it. Opening only the required UI/API ports reduces risk. RabbitMQ should stay private because it controls internal messaging for the system.

## 3. SSH into the Azure VM

From your local machine:

```bash
ssh <azure-vm-user>@<azure-vm-public-ip>
```

Why: The first deployment needs one-time server preparation. GitHub Actions can deploy automatically later, but Docker, Git, the repo, and `.env` must exist on the VM first.

## 4. Install Docker and Docker Compose

Run this on the VM:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Then log out and SSH back in:

```bash
exit
ssh <azure-vm-user>@<azure-vm-public-ip>
```

Verify Docker:

```bash
docker --version
docker compose version
```

Why: Docker runs the application containers. Docker Compose reads `docker-compose.yml` and starts all services together with the correct network, ports, volumes, and dependencies.

## 5. Clone the deployment branch on the VM

Run this on the VM:

```bash
sudo mkdir -p /opt
sudo chown $USER:$USER /opt
cd /opt
git clone -b deployment_1 <your-github-repo-url> Ominifix-AI_Enhanced_Self_Healing_RPA_Framework
cd Ominifix-AI_Enhanced_Self_Healing_RPA_Framework
```

Why: The GitHub Actions workflow deploys the `deployment_1` branch. The VM must also use that same branch so the code running on Azure matches the branch that triggers the pipeline.

## 6. Create the production `.env` file on the VM

Run this inside the repo on the VM:

```bash
cp .env.template .env
nano .env
```

At minimum, change:

```bash
RABBITMQ_DEFAULT_USER=ominifix
RABBITMQ_DEFAULT_PASS=<strong-password>
```

Do not commit `.env`.

Why: Real credentials and deployment-specific settings should not be stored in Git. The Compose file reads `.env` on the VM, so secrets stay on the server while the repo keeps only a safe template.

## 7. Create the RabbitMQ Docker volume

Run this on the VM:

```bash
docker volume create ominifix_rabbitmq_data
```

Why: The Compose file expects an external volume named `ominifix_rabbitmq_data`. This keeps RabbitMQ data outside the container lifecycle, so messages and broker state are not removed every time containers are rebuilt.

## 8. Do the first manual deployment

Run this on the VM:

```bash
docker compose up -d --build
docker compose ps
```

Check logs if a service fails:

```bash
docker compose logs --tail=100 <service-name>
```

Why: The first manual deployment proves the VM, Docker installation, `.env`, volumes, ports, and Compose file work before GitHub Actions is added. This makes CI/CD troubleshooting much easier.

## 9. Prepare an SSH key for GitHub Actions

On your local machine, create a deploy key if you do not already have one:

```bash
ssh-keygen -t ed25519 -C "github-actions-ominifix-azure" -f ~/.ssh/ominifix_azure_deploy
```

Copy the public key to the VM:

```bash
ssh-copy-id -i ~/.ssh/ominifix_azure_deploy.pub <azure-vm-user>@<azure-vm-public-ip>
```

Test it:

```bash
ssh -i ~/.ssh/ominifix_azure_deploy <azure-vm-user>@<azure-vm-public-ip>
```

Why: GitHub Actions needs secure, non-interactive SSH access to the Azure VM. The workflow uses this key to run deployment commands remotely.

## 10. Add GitHub repository secrets

In GitHub, open:

```text
Repository -> Settings -> Secrets and variables -> Actions -> New repository secret
```

Add:

```text
VM_HOST=<azure-vm-public-ip-or-dns-name>
VM_USER=<azure-vm-username>
VM_SSH_KEY=<contents-of-private-key>
```

Optional:

```text
VM_PROJECT_PATH=/opt/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework
```

To print the private key for `VM_SSH_KEY`:

```bash
cat ~/.ssh/ominifix_azure_deploy
```

Why: Secrets let GitHub Actions connect to Azure without hardcoding private credentials in the repo. `VM_PROJECT_PATH` is optional because the workflow already has the `/opt/...` default path.

## 11. Confirm the GitHub Actions workflow

The workflow file is:

```text
.github/workflows/deploy.yml
```

It is configured to run on pushes to:

```text
deployment_1
```

The important deploy commands are:

```bash
git pull origin deployment_1
docker volume create ominifix_rabbitmq_data || true
docker compose up -d --build --remove-orphans
docker compose ps
```

Why: The pipeline should deploy the same branch you are actively using for deployment. The `docker compose up -d --build --remove-orphans` command rebuilds changed services, restarts them in the background, and removes containers that no longer exist in the Compose file.

## 12. Push to trigger CI/CD

From your local repo:

```bash
git status
git add .
git commit -m "Add Azure VM Docker Compose deployment pipeline"
git push origin deployment_1
```

Then check:

```text
GitHub -> Actions -> Deploy Ominifix
```

Why: A push to `deployment_1` is the deployment trigger. GitHub Actions validates the Compose configuration first, then deploys to the Azure VM only if validation succeeds.

## 13. Verify the Azure deployment

On the VM:

```bash
cd /opt/Ominifix-AI_Enhanced_Self_Healing_RPA_Framework
docker compose ps
docker compose logs --tail=100
```

From your browser, open the exposed services using the VM public IP:

```text
http://<azure-vm-public-ip>:3000
http://<azure-vm-public-ip>:5173
http://<azure-vm-public-ip>:8601
```

Why: CI/CD success only means the deployment commands completed. You still need to verify the containers are healthy and the user-facing dashboards are reachable through Azure networking.

## 14. Recommended next hardening step

After the basic pipeline works, add Nginx or Traefik in front of the services and expose only HTTP/HTTPS:

```text
80/tcp
443/tcp
```

Then close the individual service ports in Azure.

Why: Directly exposing many service ports is acceptable for a controlled demo, but it is not ideal for public deployment. A reverse proxy gives one public entry point, cleaner URLs, TLS support, and better control over which services are reachable.

## Important Security Notes

- Do not use RabbitMQ `guest/guest`.
- Keep `.env` only on the VM.
- Keep RabbitMQ ports closed publicly.
- Use a dedicated Azure VM for this project.
- Review this Docker socket mount carefully:

```yaml
- /var/run/docker.sock:/var/run/docker.sock
```

Why: The Docker socket mount gives the orchestrator container control over Docker on the host. That may be required for self-healing restarts, but it is a high-trust permission.
