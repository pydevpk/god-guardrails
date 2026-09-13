import yaml

class PolicyLoader:
    def __init__(self, path: str):
        with open(path, "r") as f:
            self.policies = yaml.safe_load(f)

    def get_policies(self, app_id: str):
        global_policies = self.policies.get("global", {})
        app_policies = self.policies.get("applications", {})
        return {"global_policies": global_policies, "application_policies": app_policies}