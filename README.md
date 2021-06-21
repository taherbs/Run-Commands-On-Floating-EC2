# Run commands on Floating EC2 instances
[![MIT licensed](https://img.shields.io/badge/license-apache2-blue.svg)](https://github.com/taherbs/Run-Commands-On-Floating-EC2/master/LICENSE)

This project allows you to run remote code on Floating EC2 instances.

The code will:
* Create an EC2 instance based on the AMI ID you provide.
* Run the command/script you provide via SSM.
* Delete the EC2 instance once the job is done.

This process could be used to schedule heavy tasks execution that cannot be containerized on Windows/Linux EC2 instances (like rendering and enormos builds) on AWS.

### Prerequisites

- python3
- pip
- virtualenv
- [AWS-CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html)
- [AWS Access Keys](https://docs.aws.amazon.com/powershell/latest/userguide/pstools-appendix-sign-up.html) with the privilges to:
  -  Create/destroy EC2 instances
  -  SSM get/list/run commands
- IAM instance-profile with the "AmazonSSMManagedInstanceCore" policy attached to it
- S3 bucket to store the job logs

### Installation

* Clone the project and create/activate virtualenv.
* Install needed libraries.

```powershell
# On Windows
cd PROJECT_PATH
virtualenv .env # Create virtualenv - only the first time
.\.env\Scripts\activate # Activate virtualenv
pip install -r requirements.txt # install required packages
```

```bash
# On Linux
cd PROJECT_PATH
virtualenv .env # Create virtualenv - only the first time
. .env/bin/activate # Activate virtualenv
python3 -m pip install -r requirements.txt # install required packages
```

### Load AWS credentials
```powershell
# On Windows
aws configure --profile "PROFILE_NAME"
$env:AWS_PROFILE="PROFILE_NAME"
# Or
$env:AWS_DEFAULT_REGION="ca-central-1"
$env:AWS_ACCESS_KEY_ID="XXX-XXX-XXX-XXX"
$env:AWS_SECRET_ACCESS_KEY="XXXXXXXXXXXXXXX"
```

```bash
aws configure --profile "PROFILE_NAME"
export AWS_PROFILE="PROFILE_NAME"
# Or
export AWS_DEFAULT_REGION="ca-central-1"
export AWS_ACCESS_KEY_ID="XXX-XXX-XXX-XXX"
export AWS_SECRET_ACCESS_KEY="XXXXXXXXXXXXXXX"
```

### Configuration
The service configuration is stored in the ***config/settings.yml*** file.<br>
Use the [config/settings.yml.sample](./config/settings.yml.sample) as a base.

### How to run

#### How to use on Windows example:

```powershell
python .\handler.py -a "ami-XXXXXX" -p "YOUR_PROJECT_NAME" -c @"
`$ErrorActionPreference = 'Stop'
git clone https://github.com/taherbs/scriptbox.git c:/scriptbox
if (-not `$?) { throw \"clone command failed\"}
cd "c:/scriptbox"
./run_script.ps1
"@
```

#### How to use on Linux example:

```bash
COMMAND_EXEC=$(cat <<-END
\$ErrorActionPreference = 'Stop'
git clone https://github.com/taherbs/scriptbox.git c:/scriptbox
if (-not \$?) { throw "clone command failed"}
cd "c:/scriptbox"
./run_script.ps1
END)
python ./handler.py -a "test" -p "rendering-farm-foxtrot" -c "$COMMAND_EXEC"
```

### TO_DO
* Change the instance type to spot to optimize cost
* Better logging when error
