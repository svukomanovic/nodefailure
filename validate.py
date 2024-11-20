import json
import subprocess

def get_node_list():
    """Retrieve the list of node names from the Kubernetes cluster."""
    cmd = ['kubectl', 'get', 'nodes', '-o', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    nodes_data = json.loads(result.stdout)
    node_names = [node['metadata']['name'] for node in nodes_data['items']]
    return node_names

def select_node(node_names):
    """Prompt the user to select a node from the list."""
    print("Available Nodes:")
    for idx, name in enumerate(node_names, start=1):
        print(f"{idx}. {name}")
    while True:
        try:
            choice = int(input("Select a node by entering the corresponding number: "))
            if 1 <= choice <= len(node_names):
                return node_names[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(node_names)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_pods_on_node(node_name):
    """Retrieve pods running on the selected node."""
    cmd = [
        'kubectl', 'get', 'pods', '--all-namespaces',
        '--field-selector', f'spec.nodeName={node_name}', '-o', 'json'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def extract_containers(pods_data):
    """Extract container names from pods data."""
    containers = set()
    for pod in pods_data['items']:
        for container in pod['spec']['containers']:
            containers.add(container['name'])
    return containers

def load_container_info():
    """Load predefined container information from a JSON file."""
    with open('container_info.json') as f:
        return json.load(f)

def assess_impact(containers, container_info):
    """Assess the impact based on container criticality and dependencies."""
    reports = []
    for container in containers:
        info = container_info.get(container, {
            'description': 'No information available',
            'dependencies': [],
            'criticality': 'unknown'
        })
        impact = 'Unknown impact'
        if info['criticality'] == 'high':
            impact = 'High impact'
        elif info['criticality'] == 'medium':
            impact = 'Moderate impact'
        elif info['criticality'] == 'low':
            impact = 'Low impact'
        reports.append({
            'container_name': container,
            'description': info['description'],
            'dependencies': info['dependencies'],
            'criticality': info['criticality'],
            'impact': impact
        })
    return reports

def main():
    node_names = get_node_list()
    if not node_names:
        print("No nodes found in the cluster.")
        return
    selected_node = select_node(node_names)
    print(f"\nSelected Node: {selected_node}\n")
    pods_data = get_pods_on_node(selected_node)
    containers = extract_containers(pods_data)
    if not containers:
        print(f"No containers running on node {selected_node}.")
        return
    container_info = load_container_info()
    impact_reports = assess_impact(containers, container_info)

    # Output the impact report
    print("Impact Assessment Report:")
    print("=" * 40)
    for report in impact_reports:
        print(f"Container: {report['container_name']}")
        print(f"Description: {report['description']}")
        print(f"Dependencies: {', '.join(report['dependencies']) if report['dependencies'] else 'None'}")
        print(f"Criticality: {report['criticality']}")
        print(f"Impact: {report['impact']}")
        print('-' * 40)

if __name__ == '__main__':
    main()
