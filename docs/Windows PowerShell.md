Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

Install the latest PowerShell for new features and improvements! https://aka.ms/PSWindows

PS C:\WINDOWS\system32> choco install minikube kubernetes-cli -y
Chocolatey v2.4.3
Installing the following packages:
minikube;kubernetes-cli
By installing, you accept licenses for the packages.
Downloading package from source 'https://community.chocolatey.org/api/v2/'
Progress: Downloading kubernetes-cli 1.35.3... 100%

kubernetes-cli v1.35.3 [Approved]
kubernetes-cli package files install completed. Performing other installation steps.
Extracting 64-bit C:\ProgramData\chocolatey\lib\kubernetes-cli\tools\kubernetes-client-windows-amd64.tar.gz to C:\ProgramData\chocolatey\lib\kubernetes-cli\tools...
C:\ProgramData\chocolatey\lib\kubernetes-cli\tools
Extracting 64-bit C:\ProgramData\chocolatey\lib\kubernetes-cli\tools\kubernetes-client-windows-amd64.tar to C:\ProgramData\chocolatey\lib\kubernetes-cli\tools...
C:\ProgramData\chocolatey\lib\kubernetes-cli\tools
 ShimGen has successfully created a shim for kubectl-convert.exe
 ShimGen has successfully created a shim for kubectl.exe
 The install of kubernetes-cli was successful.
  Deployed to 'C:\ProgramData\chocolatey\lib\kubernetes-cli\tools'
Downloading package from source 'https://community.chocolatey.org/api/v2/'
Progress: Downloading Minikube 1.38.1... 100%

Minikube v1.38.1 [Approved]
Minikube package files install completed. Performing other installation steps.
 ShimGen has successfully created a shim for minikube.exe
 The install of Minikube was successful.
  Deployed to 'C:\ProgramData\chocolatey\lib\Minikube'

Chocolatey installed 2/2 packages.
 See the log for details (C:\ProgramData\chocolatey\logs\chocolatey.log).
PS C:\WINDOWS\system32> choco install python --version=3.11.0 -y
Chocolatey v2.4.3
Installing the following packages:
python
By installing, you accept licenses for the packages.
A newer version of python (v3.13.5) is already installed.
 Use --allow-downgrade or --force to attempt to install older versions.

Chocolatey installed 0/1 packages. 1 packages failed.
 See the log for details (C:\ProgramData\chocolatey\logs\chocolatey.log).

Failures
 - python - A newer version of python (v3.13.5) is already installed.
 Use --allow-downgrade or --force to attempt to install older versions.
PS C:\WINDOWS\system32> minikube start --driver=docker --memory=4096 --cpus=2
* minikube v1.38.1 on Microsoft Windows 11 Home Single Language 25H2
* Using the docker driver based on user configuration

X Exiting due to PROVIDER_DOCKER_VERSION_EXIT_1: "docker version --format <no value>-<no value>:<no value>" exit status 1: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
* Documentation: https://minikube.sigs.k8s.io/docs/drivers/docker/

PS C:\WINDOWS\system32> docker --version
Docker version 29.1.5, build 0e6fee6
PS C:\WINDOWS\system32> docker --version
Docker version 29.3.1, build c2be9cc
PS C:\WINDOWS\system32> wsl --install
Downloading: Ubuntu
Installing: Ubuntu
Distribution successfully installed. It can be launched via 'wsl.exe -d Ubuntu'
Launching Ubuntu...
Provisioning the new WSL instance Ubuntu
This might take a while...
Create a default Unix user account: asmit
New password:
Retype new password:
passwd: password updated successfully
To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.

asmit@Ash10:/mnt/c/WINDOWS/system32$ docker ps

The command 'docker' could not be found in this WSL 2 distro.
We recommend to activate the WSL integration in Docker Desktop settings.

For details about using Docker Desktop with WSL 2, visit:

https://docs.docker.com/go/wsl2/

asmit@Ash10:/mnt/c/WINDOWS/system32$ wsl --shutdown
wsl: command not found
asmit@Ash10:/mnt/c/WINDOWS/system32$ exit
exit
PS C:\WINDOWS\system32> wsl --shutdown
PS C:\WINDOWS\system32> wsl
To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.

asmit@Ash10:/mnt/c/WINDOWS/system32$ docker ps
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
asmit@Ash10:/mnt/c/WINDOWS/system32$ minikube start --driver=docker --memory=4096 --cpus=2
minikube: command not found
asmit@Ash10:/mnt/c/WINDOWS/system32$ exit
logout
PS C:\WINDOWS\system32> minikube start --driver=docker --memory=4096 --cpus=2
* minikube v1.38.1 on Microsoft Windows 11 Home Single Language 25H2
* Using the docker driver based on user configuration
! Starting v1.39.0, minikube will default to "containerd" container runtime. See #21973 for more info.
* Using Docker Desktop driver with root privileges
* Starting "minikube" primary control-plane node in "minikube" cluster
* Pulling base image v0.0.50 ...
* Downloading Kubernetes v1.35.1 preload ...
    > preloaded-images-k8s-v18-v1...:  272.45 MiB / 272.45 MiB  100.00% 918.25
    > gcr.io/k8s-minikube/kicbase...:  519.58 MiB / 519.58 MiB  100.00% 1.57 Mi
* Creating docker container (CPUs=2, Memory=4096MB) ...
! Failing to connect to https://registry.k8s.io/ from inside the minikube container
* To pull new external images, you may need to configure a proxy: https://minikube.sigs.k8s.io/docs/reference/networking/proxy/
* Preparing Kubernetes v1.35.1 on Docker 29.2.1 ...
* Configuring bridge CNI (Container Networking Interface) ...
* Verifying Kubernetes components...
  - Using image gcr.io/k8s-minikube/storage-provisioner:v5
* Enabled addons: storage-provisioner, default-storageclass
* Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
PS C:\WINDOWS\system32> minikube version
minikube version: v1.38.1
commit: c93a4cb9311efc66b90d33ea03f75f2c4120e9b0
PS C:\WINDOWS\system32> kubectl version --client
Client Version: v1.35.3
Kustomize Version: v5.7.1
PS C:\WINDOWS\system32> pip install kubernetes
Collecting kubernetes
  Downloading kubernetes-35.0.0-py2.py3-none-any.whl.metadata (1.7 kB)
Requirement already satisfied: certifi>=14.05.14 in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from kubernetes) (2025.1.31)
Requirement already satisfied: six>=1.9.0 in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from kubernetes) (1.17.0)
Requirement already satisfied: python-dateutil>=2.5.3 in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from kubernetes) (2.9.0.post0)
Requirement already satisfied: pyyaml>=5.4.1 in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from kubernetes) (6.0.2)
Requirement already satisfied: websocket-client!=0.40.0,!=0.41.*,!=0.42.*,>=0.32.0 in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from kubernetes) (1.8.0)
Requirement already satisfied: requests in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from kubernetes) (2.32.3)
Collecting requests-oauthlib (from kubernetes)
  Downloading requests_oauthlib-2.0.0-py2.py3-none-any.whl.metadata (11 kB)
Requirement already satisfied: urllib3!=2.6.0,>=1.24.2 in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from kubernetes) (2.3.0)
Collecting durationpy>=0.7 (from kubernetes)
  Downloading durationpy-0.10-py3-none-any.whl.metadata (340 bytes)
Requirement already satisfied: charset-normalizer<4,>=2 in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from requests->kubernetes) (3.4.1)
Requirement already satisfied: idna<4,>=2.5 in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (from requests->kubernetes) (3.10)
Collecting oauthlib>=3.0.0 (from requests-oauthlib->kubernetes)
  Downloading oauthlib-3.3.1-py3-none-any.whl.metadata (7.9 kB)
Downloading kubernetes-35.0.0-py2.py3-none-any.whl (2.0 MB)
   ---------------------------------------- 2.0/2.0 MB 3.1 MB/s eta 0:00:00
Downloading durationpy-0.10-py3-none-any.whl (3.9 kB)
Downloading requests_oauthlib-2.0.0-py2.py3-none-any.whl (24 kB)
Downloading oauthlib-3.3.1-py3-none-any.whl (160 kB)
Installing collected packages: durationpy, oauthlib, requests-oauthlib, kubernetes
Successfully installed durationpy-0.10 kubernetes-35.0.0 oauthlib-3.3.1 requests-oauthlib-2.0.0

[notice] A new release of pip is available: 25.1.1 -> 26.0.1
[notice] To update, run: python.exe -m pip install --upgrade pip
PS C:\WINDOWS\system32> python.exe -m pip install --upgrade pip
Requirement already satisfied: pip in c:\users\asmit\appdata\local\programs\python\python313\lib\site-packages (25.1.1)
Collecting pip
  Using cached pip-26.0.1-py3-none-any.whl.metadata (4.7 kB)
Using cached pip-26.0.1-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 25.1.1
    Uninstalling pip-25.1.1:
      Successfully uninstalled pip-25.1.1
Successfully installed pip-26.0.1
PS C:\WINDOWS\system32> pip install pyyaml
Requirement already satisfied: pyyaml in C:\Users\ASMIT\AppData\Local\Programs\Python\Python313\Lib\site-packages (6.0.2)
PS C:\WINDOWS\system32> cd C:\
>> mkdir k8swhisperer
>>


    Directory: C:\


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        29-03-2026  11.42 AM                k8swhisperer


PS C:\> cd k8swhisperer
>> mkdir tools
>> mkdir scenarios
>> mkdir rbac
>> mkdir tests
>>


    Directory: C:\k8swhisperer


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        29-03-2026  11.42 AM                tools
d-----        29-03-2026  11.42 AM                scenarios
d-----        29-03-2026  11.42 AM                rbac
d-----        29-03-2026  11.42 AM                tests