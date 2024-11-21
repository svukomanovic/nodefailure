import json
import subprocess
import os

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
    """Extract container names and namespaces from pods data."""
    containers = []
    for pod in pods_data['items']:
        namespace = pod['metadata']['namespace']
        pod_name = pod['metadata']['name']
        for container in pod['spec']['containers']:
            containers.append({
                'namespace': namespace,
                'pod_name': pod_name,
                'container_name': container['name']
            })
    return containers

def load_container_info():
    """Load predefined container information from a JSON file."""
    with open('container_info.json') as f:
        return json.load(f)

def assess_impact(containers, container_info):
    """Assess the impact based on container criticality and dependencies."""
    reports = []
    missing_containers = []
    for container in containers:
        namespace = container['namespace']
        container_name = container['container_name']
        pod_name = container['pod_name']

        info = container_info.get(namespace, {}).get(container_name)
        if info is None:
            missing_containers.append((namespace, container_name))
            info = {
                'description': 'No information available',
                'dependencies': [],
                'criticality': 'unknown'
            }

        criticality = info.get('criticality', 'unknown')
        if criticality == 'high':
            impact = 'High impact'
        elif criticality == 'medium':
            impact = 'Moderate impact'
        elif criticality == 'low':
            impact = 'Low impact'
        else:
            impact = 'Unknown impact'

        reports.append({
            'namespace': namespace,
            'pod_name': pod_name,
            'container_name': container_name,
            'description': info.get('description', 'No information available'),
            'dependencies': info.get('dependencies', []),
            'criticality': criticality,
            'impact': impact
        })
    return reports, missing_containers

def print_report(impact_reports):
    """Print the impact report and save it to a text file."""
    report_lines = []
    report_lines.append("Impact Assessment Report:")
    report_lines.append("=" * 60)
    for report in impact_reports:
        report_lines.append(f"Namespace: {report['namespace']}")
        report_lines.append(f"Pod: {report['pod_name']}")
        report_lines.append(f"Container: {report['container_name']}")
        report_lines.append(f"Description: {report['description']}")
        report_lines.append(f"Dependencies: {', '.join(report['dependencies']) if report['dependencies'] else 'None'}")
        report_lines.append(f"Criticality: {report['criticality']}")
        report_lines.append(f"Impact: {report['impact']}")
        report_lines.append('-' * 60)

    report_text = '\n'.join(report_lines)
    print(report_text)

    # Save to a text file
    with open('impact_report.txt', 'w') as f:
        f.write(report_text)
    print("\nReport saved to 'impact_report.txt'.")

def gather_statistics(impact_reports):
    """Gather and display report statistics."""
    while True:
        print("\nReport Statistics Menu:")
        print("A) Count how many critical containers are there")
        print("B) List all containers with criticality and dependencies")
        print("C) Go back to main menu")
        choice = input("Select an option (A/B/C): ").strip().upper()

        if choice == 'A':
            count_critical_containers(impact_reports)
        elif choice == 'B':
            list_containers_with_details(impact_reports)
        elif choice == 'C':
            break
        else:
            print("Invalid choice. Please select A, B, or C.")

def count_critical_containers(impact_reports):
    """Count and display the number of critical containers."""
    critical_count = sum(1 for report in impact_reports if report['criticality'] == 'high')
    print(f"\nTotal number of critical containers: {critical_count}")

def list_containers_with_details(impact_reports):
    """List all containers with their criticality and dependencies."""
    # Determine the maximum length for alignment
    container_names = [f"{report['namespace']}/{report['container_name']}" for report in impact_reports]
    max_name_length = max(len(name) for name in container_names) if container_names else 0

    print("\nContainers Summary:")
    print("=" * (max_name_length + 50))
    print(f"{'Container Name':<{max_name_length}}  | Criticality | Dependencies")
    print('-' * (max_name_length + 50))
    for report in impact_reports:
        container_full_name = f"{report['namespace']}/{report['container_name']}"
        criticality = report['criticality'].capitalize()
        dependencies = ', '.join(report['dependencies']) if report['dependencies'] else 'None'
        print(f"{container_full_name:<{max_name_length}}  | {criticality:^11} | {dependencies}")
    print('=' * (max_name_length + 50))

def main_menu(impact_reports):
    """Display the main menu and handle user choices."""
    while True:
        print("\nMain Menu:")
        print("1. Print out the report")
        print("2. Gather report statistics")
        print("3. Quit and save the report file")
        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == '1':
            print_report(impact_reports)
        elif choice == '2':
            gather_statistics(impact_reports)
        elif choice == '3':
            # Save the report file before quitting
            print_report(impact_reports)
            print("Exiting. Report saved.")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

def main():
    # Check if container_info.json exists
    if not os.path.exists('container_info.json'):
        print("container_info.json not found. Please run the template generation script and fill in the required information.")
        return

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
    impact_reports, missing_containers = assess_impact(containers, container_info)

    if missing_containers:
        print("\nWarning: Some containers are missing from container_info.json:")
        for namespace, container_name in missing_containers:
            print(f"Namespace: {namespace}, Container: {container_name}")
        print("Consider updating container_info.json with these containers.")

    main_menu(impact_reports)

if __name__ == '__main__':
    main()
