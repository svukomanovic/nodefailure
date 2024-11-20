import json
import subprocess

def get_pods_on_node(node_name):
    cmd = [
        'kubectl', 'get', 'pods', '--all-namespaces',
        '--field-selector', f'spec.nodeName={node_name}', '-o', 'json'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def extract_containers(pods_data):
    containers = set()
    for pod in pods_data['items']:
        for container in pod['spec']['containers']:
            containers.add(container['name'])
    return containers

def load_container_info():
    with open('container_info.json') as f:
        return json.load(f)

def assess_impact(containers, container_info):
    reports = []
    for container in containers:
        info = container_info.get(container, {
            'description': 'No information available',
            'dependencies': [],
            'criticality': 'unknown'
        })
        impact = 'Unknown impact' if info['criticality'] == 'unknown' else (
            'High impact' if info['criticality'] == 'high' else 'Moderate impact'
        )
        reports.append({
            'container_name': container,
            'description': info['description'],
            'dependencies': info['dependencies'],
            'criticality': info['criticality'],
            'impact': impact
        })
    return reports

def main(node_name):
    pods_data = get_pods_on_node(node_name)
    containers = extract_containers(pods_data)
    container_info = load_container_info()
    impact_reports = assess_impact(containers, container_info)

    # Output the impact report
    for report in impact_reports:
        print(f"Container: {report['container_name']}")
        print(f"Description: {report['description']}")
        print(f"Dependencies: {', '.join(report['dependencies'])}")
        print(f"Criticality: {report['criticality']}")
        print(f"Impact: {report['impact']}")
        print('-' * 40)

if __name__ == '__main__':
    node_name = 'node1'  # Replace with your node name
    main(node_name)
