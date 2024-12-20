import json
import subprocess
import os
from datetime import datetime

def save_session_data():
    """Retrieve node and pod information and save it to session.json."""
    # Retrieve nodes
    cmd_nodes = ['kubectl', 'get', 'nodes', '-o', 'json']
    result_nodes = subprocess.run(cmd_nodes, capture_output=True, text=True)
    nodes_data = json.loads(result_nodes.stdout)

    # Retrieve pods
    cmd_pods = ['kubectl', 'get', 'pods', '--all-namespaces', '-o', 'json']
    result_pods = subprocess.run(cmd_pods, capture_output=True, text=True)
    pods_data = json.loads(result_pods.stdout)

    # Save to session.json
    session_data = {
        'nodes': nodes_data,
        'pods': pods_data
    }
    with open('session.json', 'w') as f:
        json.dump(session_data, f, indent=4)
    print("Session data saved to 'session.json'.")

def load_session_data():
    """Load node and pod information from session.json."""
    if not os.path.exists('session.json'):
        print("session.json not found. Please run the script to generate session data.")
        return None
    with open('session.json', 'r') as f:
        session_data = json.load(f)
    return session_data

def get_node_list(session_data):
    """Retrieve the list of node names from the session data."""
    nodes_data = session_data['nodes']
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

def get_pods_on_node(session_data, node_name):
    """Retrieve pods running on the selected node from session data."""
    pods_data = session_data['pods']
    pods_on_node = {
        'items': [
            pod for pod in pods_data['items']
            if pod['spec'].get('nodeName') == node_name
        ]
    }
    return pods_on_node

def get_pods_all_nodes(session_data):
    """Retrieve pods running on all nodes from session data."""
    return session_data['pods']

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
    if not os.path.exists('container_info.json'):
        print("container_info.json not found. Please provide the container information.")
        return None
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

    # Prepare the report content
    report_lines = []
    report_lines.append(report_title)
    report_lines.append("=" * 80)
    report_lines.append(f"Date: {current_datetime}")
    report_lines.append("=" * 80)

    if selected_node:
        # Generate detailed report for individual node
        for report in impact_reports:
            report_lines.append(f"Namespace: {report['namespace']}")
            report_lines.append(f"Pod: {report['pod_name']}")
            report_lines.append(f"Container: {report['container_name']}")
            report_lines.append(f"Description: {report['description']}")
            report_lines.append(f"Dependencies: {', '.join(report['dependencies']) if report['dependencies'] else 'None'}")
            report_lines.append(f"Criticality: {report['criticality']}")
            report_lines.append(f"Impact: {report['impact']}")
            report_lines.append('-' * 80)

        # Include the table report in the printed report
        table_lines = generate_table_report(impact_reports)
        report_text = '\n'.join(report_lines + ['\n'] + table_lines)
    else:
        # For combined report, generate tables per node
        nodes = sorted(set(report['node_name'] for report in impact_reports))
        for node in nodes:
            node_reports = [report for report in impact_reports if report['node_name'] == node]
            report_lines.append(f"\nNode: {node}")
            report_lines.append('-' * 80)
            table_lines = generate_table_per_node(node_reports)
            report_lines.extend(table_lines)

        report_text = '\n'.join(report_lines)

    print(report_text)

    # Save to a text file with date and node name in the filename
    with open(report_filename, 'w') as f:
        f.write(report_text)
    print(f"\nReport saved to '{report_filename}'.")

def generate_table_per_node(node_reports):
    """Generate a table report for a specific node."""
    # Sort the reports by criticality
    sorted_reports = sorted(node_reports, key=lambda x: x['criticality_sort'])

    # Determine the maximum length for alignment
    container_names = [f"{report['namespace']}/{report['container_name']}" for report in sorted_reports]
    max_name_length = max(len(name) for name in container_names) if container_names else 0

    table_lines = []
    table_lines.append(f"{'Container Name':<{max_name_length}}  | Criticality | Dependencies")
    table_lines.append('-' * (max_name_length + 50))
    for report in sorted_reports:
        container_full_name = f"{report['namespace']}/{report['container_name']}"
        criticality = report['criticality'].capitalize()
        dependencies = ', '.join(report['dependencies']) if report['dependencies'] else 'None'
        line = f"{container_full_name:<{max_name_length}}  | {criticality:^11} | {dependencies}"
        table_lines.append(line)
    table_lines.append('=' * (max_name_length + 50))
    return table_lines

def generate_table_report(impact_reports):
    """Generate a table report sorted by criticality from High to Low."""
    # Sort the reports by criticality
    sorted_reports = sorted(impact_reports, key=lambda x: x['criticality_sort'])

    # Determine the maximum length for alignment
    container_names = [f"{report['namespace']}/{report['container_name']}" for report in sorted_reports]
    max_name_length = max(len(name) for name in container_names) if container_names else 0

    table_lines = []
    table_lines.append("Containers Summary:")
    table_lines.append("=" * (max_name_length + 50))
    table_lines.append(f"{'Container Name':<{max_name_length}}  | Criticality | Dependencies")
    table_lines.append('-' * (max_name_length + 50))
    for report in sorted_reports:
        container_full_name = f"{report['namespace']}/{report['container_name']}"
        criticality = report['criticality'].capitalize()
        dependencies = ', '.join(report['dependencies']) if report['dependencies'] else 'None'
        line = f"{container_full_name:<{max_name_length}}  | {criticality:^11} | {dependencies}"
        table_lines.append(line)
    table_lines.append('=' * (max_name_length + 50))
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

def generate_consolidated_json(impact_reports):
    """Generate a consolidated JSON file with the impact reports."""
    # Get current date and time for the filename (exclude seconds)
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"consolidated_{current_datetime}.json"

    # Organize the reports by node
    nodes = sorted(set(report['node_name'] for report in impact_reports))
    consolidated_data = {}
    for node in nodes:
        node_reports = [report for report in impact_reports if report['node_name'] == node]
        consolidated_data[node] = node_reports

    # Save to a JSON file
    with open(filename, 'w') as f:
        json.dump(consolidated_data, f, indent=4)
    print(f"\nConsolidated data saved to '{filename}'.")

def generate_graph_data_json(impact_reports):
    """Generate a JSON file containing graph data structured per node."""
    # Organize the reports by node
    nodes = sorted(set(report['node_name'] for report in impact_reports))
    graph_data = {}
    for node in nodes:
        node_reports = [report for report in impact_reports if report['node_name'] == node]
        node_graph = {
            'nodes': [],
            'edges': []
        }
        # Build node list and edges
        for report in node_reports:
            container_full_name = f"{report['namespace']}/{report['container_name']}"
            node_graph['nodes'].append({
                'id': container_full_name,
                'label': container_full_name,
                'criticality': report['criticality'],
                'description': report['description'],
                'dependencies': report['dependencies']
            })
            # Add edges for dependencies
            for dep in report['dependencies']:
                node_graph['edges'].append({
                    'from': container_full_name,
                    'to': dep
                })
        graph_data[node] = node_graph

    # Save to a JSON file
    filename = "graph_data.json"
    with open(filename, 'w') as f:
        json.dump(graph_data, f, indent=4)
    print(f"\nGraph data saved to '{filename}'.")

def main_menu(impact_reports, selected_node):
    """Display the main menu and handle user choices."""
    while True:
        print("\nMain Menu:")
        print("1. Gather report statistics")
        print("2. Print out the report")
        print("3. Generate consolidated JSON file")
        print("4. Generate graph data JSON file for Jupyter notebook")
        print("5. Quit")
        choice = input("Enter your choice (1/2/3/4/5): ").strip()

        if choice == '1':
            gather_statistics(impact_reports)
        elif choice == '2':
            print_report(impact_reports, selected_node)
        elif choice == '3':
            generate_consolidated_json(impact_reports)
        elif choice == '4':
            generate_graph_data_json(impact_reports)
        elif choice == '5':
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please select 1, 2, 3, 4, or 5.")

def main():
    # Check if session.json exists
    if not os.path.exists('session.json'):
        print("session.json not found. Collecting session data...")
        save_session_data()

    # Load session data
    session_data = load_session_data()
    if session_data is None:
        return

    node_names = get_node_list(session_data)
    if not node_names:
        print("No nodes found in the session data.")
        return
    selected_node, is_combined = select_node(node_names)
    container_info = load_container_info()
    if container_info is None:
        return

    if is_combined:
        print("\nGenerating report for all nodes...\n")
        pods_data = get_pods_all_nodes(session_data)
    else:
        print(f"\nSelected Node: {selected_node}\n")
        pods_data = get_pods_on_node(session_data, selected_node)

    containers = extract_containers(pods_data)
    if not containers:
        print("No containers found.")
        return

    impact_reports, missing_containers = assess_impact(containers, container_info)

    if missing_containers:
        print("\nWarning: Some containers are missing from container_info.json:")
        for namespace, container_name in missing_containers:
            print(f"Namespace: {namespace}, Container: {container_name}")
        print("Consider updating container_info.json with these containers.")

    if is_combined:
        # For combined report, generate tables per node and save the report
        main_menu(impact_reports, None)
    else:
        main_menu(impact_reports, selected_node)

if __name__ == '__main__':
    main()
