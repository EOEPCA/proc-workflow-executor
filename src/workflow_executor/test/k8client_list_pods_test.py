from kubernetes import client, config

config.load_kube_config(config_file="/home/bla/.kube_t2_scaleway/config")

my_api_config = client.ApiClient()

v1 = client.CoreV1Api()
ades_namespace = "ades1-dev"
pod_list = v1.list_namespaced_pod(ades_namespace)


print("Unordered: ")
for pod in pod_list.items:
     print("%s\t%s\t%s" % (pod.metadata.name,
                           pod.status.phase,
                           pod.metadata.creation_timestamp))


pod_list.items.sort(key=lambda pod: pod.metadata.creation_timestamp)

print("\nOrdered: ")
for pod in pod_list.items:
     print("%s\t%s\t%s" % (pod.metadata.name,
                           pod.status.phase,
                           pod.metadata.creation_timestamp))


