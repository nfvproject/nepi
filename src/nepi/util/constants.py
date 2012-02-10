
TESTBED_ENVIRONMENT_SETUP = "testbed_environment_setup"

class ApplicationStatus:
    STATUS_NOT_STARTED = 0
    STATUS_RUNNING = 1
    STATUS_FINISHED = 2
    STATUS_UNDETERMINED = 3

class TestbedStatus:
    STATUS_ZERO = 0
    STATUS_SETUP = 1
    STATUS_CREATED = 2
    STATUS_CONNECTED = 3
    STATUS_CROSS_CONNECTED = 4
    STATUS_CONFIGURED = 5
    STATUS_STARTED = 6
    STATUS_STOPPED = 7
    STATUS_FAILED = 8
    STATUS_UNRESPONSIVE = 9

class DeploymentConfiguration:
    MODE_SINGLE_PROCESS = "SINGLE"
    MODE_DAEMON = "DAEMON"
    ACCESS_SSH = "SSH"
    ACCESS_LOCAL = "LOCAL"
    ERROR_LEVEL = "Error"
    DEBUG_LEVEL = "Debug"
    POLICY_FAIL = "Fail"
    POLICY_RECOVER = "Recover"
    POLICY_RESTART = "Restart"
    
    DEPLOYMENT_MODE = "deployment_mode"
    DEPLOYMENT_COMMUNICATION = "deployment_communication"

    DEPLOYMENT_HOST = "deployment_host"
    DEPLOYMENT_USER = "deployment_user"
    DEPLOYMENT_PORT = "deployment_port"
    DEPLOYMENT_KEY  = "deployment_key"
    
    DEPLOYMENT_ENVIRONMENT_SETUP = "deployment_environment_setup"
    
    ROOT_DIRECTORY = "rootDirectory"
    USE_AGENT = "useAgent"
    USE_SUDO = "useSudo"
    LOG_LEVEL = "logLevel"
    RECOVER = "recover"
    RECOVERY_POLICY = "recoveryPolicy"
    CLEAN_ROOT = "cleanRoot"



