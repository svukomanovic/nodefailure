import json
import subprocess
import os

def get_all_pods():
    """Retrieve all pods in the Kubernetes cluster."""
    cmd = ['kubectl', 'get', 'pods', '--all-namespaces', '-o', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    pods_data = json.loads(result.stdout)
    return pods_data

def extract_all_containers(pods_data):
    """Extract all container names from the pods data."""
    containers = set()
    for pod in pods_data['items']:
        for container in pod['spec']['containers']:
            containers.add(container['name'])
    return containers

def generate_container_info_template(containers):
    """Generate a template JSON for container information."""
    container_info_template = {}
    for container in containers:
        container_info_template[container] = {
            'description': 'Enter description here',
            'dependencies': [],  # List of dependent containers/services
            'criticality': 'low/medium/high'  # Enter one of 'low', 'medium', 'high'
        }
    return container_info_template

def save_template_to_file(template, filename='container_info_template.json'):
    """Save the container info template to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(template, f, indent=2)
    print(f"Template saved to {filename}. Please fill in the required information.")

def main():
    # Check if container_info.json already exists
    if os.path.exists('container_info.json'):
        print("container_info.json already exists. Using the existing file for impact assessment.")
        return  # Proceed with the existing impact assessment script
    else:
        print("container_info.json not found. Generating a template...")

    # Get all pods in the cluster
    pods_data = get_all_pods()
    if not pods_data['items']:
        print("No pods found in the cluster.")
        return

    # Extract all container names
    containers = extract_all_containers(pods_data)
    if not containers:
        print("No containers found in the pods.")
        return

    # Generate the template
    container_info_template = generate_container_info_template(containers)

    # Save the template to a file
    save_template_to_file(container_info_template)

if __name__ == '__main__':
    main()
