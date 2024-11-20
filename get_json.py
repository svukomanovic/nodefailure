import json
import subprocess
import os
import sys

def get_all_pods():
    """Retrieve all pods in the Kubernetes cluster."""
    cmd = ['kubectl', 'get', 'pods', '--all-namespaces', '-o', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error retrieving pods:", result.stderr)
        sys.exit(1)
    pods_data = json.loads(result.stdout)
    return pods_data

def extract_all_containers(pods_data):
    """Extract all container names and their namespaces from the pods data."""
    containers = {}
    for pod in pods_data['items']:
        namespace = pod['metadata']['namespace']
        for container in pod['spec']['containers']:
            container_name = container['name']
            if namespace not in containers:
                containers[namespace] = set()
            containers[namespace].add(container_name)
    return containers

def generate_container_info_template(containers):
    """Generate a template JSON for container information with namespaces."""
    container_info_template = {}
    for namespace, container_names in containers.items():
        container_info_template[namespace] = {}
        for container_name in container_names:
            container_info_template[namespace][container_name] = {
                'description': 'Enter description here',
                'dependencies': [],  # List of dependent containers/services
                'criticality': 'low/medium/high'  # Enter one of 'low', 'medium', 'high'
            }
    return container_info_template

def save_template_to_file(template, filename='container_info.json'):
    """Save the container info template to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(template, f, indent=2)
    print(f"File saved as {filename}.")

def calculate_namespace_completion(container_info):
    """Calculate the completion percentage for each namespace based on filled descriptions."""
    namespace_completion = {}
    for namespace, containers in container_info.items():
        total_containers = len(containers)
        filled_containers = 0
        for container in containers.values():
            description = container.get('description', '')
            if description and description.strip() != 'Enter description here':
                filled_containers += 1
        completion_percentage = int((filled_containers / total_containers) * 100) if total_containers > 0 else 0
        namespace_completion[namespace] = completion_percentage
    return namespace_completion

def edit_container_info(container_info):
    """Allow the user to edit the container info."""
    while True:
        # Calculate completion percentage for each namespace
        namespace_completion = calculate_namespace_completion(container_info)
        namespaces = list(container_info.keys())

        print("\nNamespaces:")
        for idx, ns in enumerate(namespaces, 1):
            completion = namespace_completion.get(ns, 0)
            print(f"{idx}. {ns} ({completion}% completed)")
        print(f"{len(namespaces)+1}. Go back to main menu")

        ns_choice = input("Select a namespace to edit (or enter number to go back): ")
        if not ns_choice.isdigit() or not (1 <= int(ns_choice) <= len(namespaces)+1):
            print("Invalid choice. Please try again.")
            continue
        ns_choice = int(ns_choice)
        if ns_choice == len(namespaces) + 1:
            break  # Go back to main menu

        selected_ns = namespaces[ns_choice - 1]
        containers = list(container_info[selected_ns].keys())

        while True:
            print(f"\nContainers in namespace '{selected_ns}':")
            for idx, container in enumerate(containers, 1):
                print(f"{idx}. {container}")
            print(f"{len(containers)+1}. Go back to namespace selection")

            cont_choice = input("Select a container to edit (or enter number to go back): ")
            if not cont_choice.isdigit() or not (1 <= int(cont_choice) <= len(containers)+1):
                print("Invalid choice. Please try again.")
                continue
            cont_choice = int(cont_choice)
            if cont_choice == len(containers) + 1:
                break  # Go back to namespace selection

            selected_cont = containers[cont_choice - 1]
            cont_info = container_info[selected_ns][selected_cont]

            # Edit description
            print(f"\nCurrent description: {cont_info['description']}")
            new_description = input("Enter new description (leave blank to keep current): ")
            if new_description.strip():
                cont_info['description'] = new_description.strip()

            # Edit criticality
            criticality_map = {'1': 'low', '2': 'medium', '3': 'high'}
            current_criticality = cont_info.get('criticality', 'unknown')
            print(f"Current criticality: {current_criticality}")
            print("Criticality options: 1. Low  2. Medium  3. High")
            new_crit = input("Enter new criticality (1/2/3, leave blank to keep current): ")
            if new_crit in criticality_map:
                cont_info['criticality'] = criticality_map[new_crit]

            # Edit dependencies
            print(f"Current dependencies: {cont_info['dependencies']}")
            dep_choice = input("Do you want to edit dependencies? (y/n): ")
            if dep_choice.lower() == 'y':
                # Get list of namespaces to choose dependencies from
                dep_namespaces = list(container_info.keys())
                dep_namespaces.append('None')
                print("\nAvailable namespaces for dependencies:")
                for idx, ns in enumerate(dep_namespaces, 1):
                    print(f"{idx}. {ns}")
                dep_ns_choice = input("Select a namespace for dependencies (or 'None' for no dependencies): ")
                if dep_ns_choice.isdigit() and 1 <= int(dep_ns_choice) <= len(dep_namespaces):
                    dep_ns_choice = int(dep_ns_choice)
                    dep_ns_selected = dep_namespaces[dep_ns_choice - 1]
                    if dep_ns_selected == 'None':
                        cont_info['dependencies'] = []
                    else:
                        dep_containers = list(container_info[dep_ns_selected].keys())
                        print(f"\nContainers in namespace '{dep_ns_selected}':")
                        for idx, dep_cont in enumerate(dep_containers, 1):
                            print(f"{idx}. {dep_cont}")
                        print(f"{len(dep_containers)+1}. Cancel dependency selection")

                        dep_cont_choice = input("Select a container to depend on (enter numbers separated by commas): ")
                        if dep_cont_choice.strip():
                            selected_indices = dep_cont_choice.split(',')
                            new_dependencies = []
                            for idx_str in selected_indices:
                                if idx_str.strip().isdigit():
                                    idx = int(idx_str.strip())
                                    if 1 <= idx <= len(dep_containers):
                                        new_dependencies.append(f"{dep_ns_selected}/{dep_containers[idx - 1]}")
                                    elif idx == len(dep_containers) + 1:
                                        break
                            cont_info['dependencies'] = new_dependencies
                else:
                    print("Invalid choice. Skipping dependency update.")

            print("\nContainer information updated successfully.")
            # Save after each edit
            save_template_to_file(container_info)

def main_menu():
    """Display the main menu and handle user choices."""
    # Load existing container_info.json if it exists
    if os.path.exists('container_info.json'):
        with open('container_info.json') as f:
            container_info = json.load(f)
    else:
        container_info = {}

    while True:
        print("\nMain Menu:")
        print("1. Generate a new container info template file")
        print("2. Edit the existing container info file")
        print("3. Save and exit")
        choice = input("Enter your choice (1/2/3): ")

        if choice == '1':
            pods_data = get_all_pods()
            containers = extract_all_containers(pods_data)
            container_info = generate_container_info_template(containers)
            save_template_to_file(container_info)
            print("New container info template generated.")
        elif choice == '2':
            if not container_info:
                print("No container info file found. Please generate a new template first.")
            else:
                edit_container_info(container_info)
        elif choice == '3':
            save_template_to_file(container_info)
            print("Exiting. Changes saved.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main_menu()
