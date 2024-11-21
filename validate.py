import json
import subprocess
import os
from datetime import datetime

def get_node_list():
    """Retrieve the list of node names from the Kubernetes cluster."""
    cmd = ['kubectl', 'get', 'nodes', '-o', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    nodes_data = json.loads(result.stdout)
    node_names = [node['metadata']['name'] for node in nodes_data['items']]
    return node_names

def select_node(node_names):
    """Prompt the user to select a node from the list, or choose to generate a combined report."""
    print("Available Nodes:")
    for idx, name in enumerate(node_names, start=1):
        print(f"{idx}. {name}")
    print(f"{len(node_names) + 1}. Generate combined report for all nodes")
    while True:
        try:
            choice = int(input("Select a node by entering the corresponding number: "))
            if 1 <= choice <= len(node_names):
                return node_names[choice - 1], False  # False indicates not a combined report
            elif choice == len(node_names) + 1:
                return None, True  # True indicates combined report
            else:
                print(f"Please enter a number between 1 and {len(node_names) + 1}.")
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

def get_pods_all_nodes():
    """Retrieve pods running on all nodes."""
    cmd = ['kubectl', 'get', 'pods', '--all-namespaces', '-o', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def extract_containers(pods_data):
    """Extract container names and namespaces from pods data."""
    containers = []
    for pod in pods_data['items']:
        namespace = pod['metadata']['namespace']
        pod_name = pod['metadata']['name']
        node_name = pod['spec'].get('nodeName', 'Unknown')
        for container in pod['spec']['containers']:
            containers.append({
                'namespace': namespace,
                'pod_name': pod_name,
                'container_name': container['name'],
                'node_name': node_name
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
        node_name = container['node_name']

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
            criticality_sort = 1
        elif criticality == 'medium':
            impact = 'Moderate impact'
            criticality_sort = 2
        elif criticality == 'low':
            impact = 'Low impact'
            criticality_sort = 3
        else:
            impact = 'Unknown impact'
            criticality_sort = 4

        reports.append({
            'namespace': namespace,
            'pod_name': pod_name,
            'container_name': container_name,
            'node_name': node_name,
            'description': info.get('description', 'No information available'),
            'dependencies': info.get('dependencies', []),
            'criticality': criticality,
            'criticality_sort': criticality_sort,
            'impact': impact
        })
    return reports, missing_containers

def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return "".join(c for c in filename if c.isalnum() or c in (' ', '_', '-')).rstrip()

def print_report(impact_reports, selected_node):
    """Print the impact report and save it to a text file with date and node name."""
    # Get current date and time for the report (exclude seconds)
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M")
    if selected_node:
        sanitized_node_name = sanitize_filename(selected_node)
        report_filename = f"{sanitized_node_name}_{current_datetime}.txt"
        report_title = f"Impact Assessment Report for Node: {selected_node}"
    else:
        report_filename = f"combined_nodes_{current_datetime}.txt"
        report_title = "Combined Impact Assessment Report for All Nodes"

    # Generate the table report
    table_lines = generate_table_report(impact_reports)

    # Prepare the report content
    report_lines = []
    report_lines.append(report_title)
    report_lines.append("=" * 80)
    report_lines.append(f"Date: {current_datetime}")
    report_lines.append("=" * 80)
    report_text = '\n'.join(report_lines + ['\n'] + table_lines)

    print(report_text)

    # Save to a text file with date and node name in the filename
    with open(report_filename, 'w') as f:
        f.write(report_text)
    print(f"\nReport saved to '{report_filename}'.")

def generate_table_report(impact_reports):
    """Generate a table report sorted by criticality from High to Low."""
    # Sort the reports by criticality
    sorted_reports = sorted(impact_reports, key=lambda x: x['criticality_sort'])

    # Determine the maximum length for alignment
    container_names = [f"{report['namespace']}/{report['container_name']}" for report in sorted_reports]
    node_names = [report['node_name'] for report in sorted_reports]
    max_name_length = max(len(name) for name in container_names) if container_names else 0
    max_node_length = max(len(name) for name in node_names) if node_names else 0

    table_lines = []
    table_lines.append("Containers Summary:")
    table_lines.append("=" * (max_name_length + max_node_length + 65))
    header = f"{'Container Name':<{max_name_length}}  | {'Node':<{max_node_length}} | Criticality | Dependencies"
    table_lines.append(header)
    table_lines.append('-' * (max_name_length + max_node_length + 65))
    for report in sorted_reports:
        container_full_name = f"{report['namespace']}/{report['container_name']}"
        node_name = report['node_name']
        criticality = report['criticality'].capitalize()
        dependencies = ', '.join(report['dependencies']) if report['dependencies'] else 'None'
        line = f"{container_full_name:<{max_name_length}}  | {node_name:<{max_node_length}} | {criticality:^11} | {dependencies}"
        table_lines.append(line)
    table_lines.append('=' * (max_name_length + max_node_length + 65))

    return table_lines

def gather_statistics(impact_reports):
    """Gather and display report statistics."""
    while True:
        print("\nReport Statistics Menu:")
        print("1. Count how many critical containers are there")
        print("2. List all containers with criticality and dependencies")
        print("3. Go back to main menu")
        choice = input("Select an option (1/2/3): ").strip()

        if choice == '1':
            count_critical_containers(impact_reports)
        elif choice == '2':
            list_containers_with_details(impact_reports)
        elif choice == '3':
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

def count_critical_containers(impact_reports):
    """Count and display the number of critical containers."""
    critical_count = sum(1 for report in impact_reports if report['criticality'] == 'high')
    print(f"\nTotal number of critical containers: {critical_count}")

def list_containers_with_details(impact_reports):
    """List all containers with their criticality and dependencies, sorted from High to Low."""
    table_lines = generate_table_report(impact_reports)
    for line in table_lines:
        print(line)

def main_menu(impact_reports, selected_node):
    """Display the main menu and handle user choices."""
    while True:
        print("\nMain Menu:")
        print("1. Gather report statistics")
        print("2. Print out the report")
        print("3. Quit")
        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == '1':
            gather_statistics(impact_reports)
        elif choice == '2':
            print_report(impact_reports, selected_node)
        elif choice == '3':
            print("Exiting.")
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
    selected_node, is_combined = select_node(node_names)
    if is_combined:
        print("\nGenerating combined report for all nodes...\n")
        pods_data = get_pods_all_nodes()
    else:
        print(f"\nSelected Node: {selected_node}\n")
        pods_data = get_pods_on_node(selected_node)
    containers = extract_containers(pods_data)
    if not containers:
        print("No containers found.")
        return
    container_info = load_container_info()
    impact_reports, missing_containers = assess_impact(containers, container_info)

    if missing_containers:
        print("\nWarning: Some containers are missing from container_info.json:")
        for namespace, container_name in missing_containers:
            print(f"Namespace: {namespace}, Container: {container_name}")
        print("Consider updating container_info.json with these containers.")

    if is_combined:
        # For combined report, only generate the table view and save the report
        print_report(impact_reports, None)
    else:
        main_menu(impact_reports, selected_node)

if __name__ == '__main__':
    main()
