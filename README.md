 # K3s Infrastructure & Observability Lab (LGTM + ELK)

Bu proje, **Infrastructure as Code (IaC)** ve **Observability** pratiklerini uygulamak amacıyla oluşturulmuş yerel bir Kubernetes laboratuvar ortamıdır. 

Proje; **Vagrant** üzerinde sanallaştırılan, **Ansible** ile configure edilen ve **K3s** üzerinde çalışan bir yapıyı kapsar. İçerisinde hem **LGTM Stack** (Loki, Grafana, Tempo, Prometheus) hem de **ELK Stack** (Elasticsearch, Logstash, Kibana) ve örnek bir Python uygulaması üzerinden log/trace takibi yapılmasına olanak tanır.
Ek olarak bir başka nodejs uygulaması üzerinden gitlab repositorysinde bulunan kod  ile beraber ArgoCD pratiklerini de barındırır. 

##  Ön Gereksinimler (Prerequisites)

Projeyi çalıştırmadan önce bilgisayarınızda aşağıdaki araçların kurulu olması gerekmektedir:

* [Vagrant](https://www.vagrantup.com/)
* [VirtualBox](https://www.virtualbox.org/)
* [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
---   

## Kurulum Adımları (Installation)

### 1. Sanal Makineyi Başlatma
Vagrant ortamını ayağa kaldırın. Bu işlem `192.168.56.10` IP adresinde bir Ubuntu sanal makinesi oluşturacaktır.

```bash
vagrant up
```

##  Altyapı ve K3s Kurulumu (Ansible)

Aşağıdaki Ansible playbook’larını **sırasıyla** çalıştırarak sunucuyu hazırlayın, K3s’i kurun ve uygulama imajını build edin.

> **Önemli:**  
> `install-k3s.yaml` adımında **geçerli bir GitLab Access Token** vermeniz gerekmektedir.

# 1. İşletim sistemi hazırlığı (Docker kurulumu, sysctl ayarları vb.)
```bash
ansible-playbook -i inventory.ini playbooks/prepare.yaml
```

# 2. K3s Kurulumu, config ayarları ve registry secret oluşturma
```bash
ansible-playbook -i inventory.ini playbooks/install-k3s.yaml \
  --extra-vars "gitlab_token=SENIN_GITLAB_TOKENIN"
```

# Chartları senkronize et ve kur
```bash
GITLAB_RUNNER_TOKEN="senin-gizli-tokenin" KUBECONFIG=./k3s.yaml helmfile sync
```


# 3. ArgoCD kurulumu
```bash
ansible-playbook -i inventory.ini playbooks/argocddeployment.yaml
```

# 4 . Python uygulamasını build et ve K3s containerd'ye import et
```bash
ansible-playbook -i inventory.ini playbooks/build-app.yaml
```


##  Erişim ve Port Yönlendirme (Access & Port Forwarding)

Servislere erişmek için aşağıdaki komutları **ayrı terminal pencerelerinde** çalıştırın.
# Grafana
```bash
KUBECONFIG=./k3s.yaml  kubectl port-forward svc/kube-prometheus-sta-grafana -n monitoring 3001:80
```

- **Grafana (LGTM Stack)**  
  URL: http://localhost:3001  
  Kullanıcı: `admin`  
  Şifre: `prom-operator` (veya Kubernetes secret içerisindeki değer)

# Kibana
```bash
KUBECONFIG=./k3s.yaml kubectl port-forward -n elk-stack svc/kibana 5601:5601 --address 0.0.0.0
```

- **Kibana (ELK Stack)**  
  URL: http://localhost:5601

# Payment App
```bash
KUBECONFIG=./k3s.yaml  kubectl --kubeconfig ./k3s.yaml port-forward svc/payment-app 5000:5000
```

- **Payment App (Test Uygulaması)**  
  API Endpoint: http://localhost:5000


##  Test ve Log Üretimi (Generating Traffic)

Sistem ayaktayken ve `payment-app` için port-forward işlemi yapılmışken, log, metric ve trace datası üretmek amacıyla aşağıdaki HTTP isteklerini gönderebilirsiniz.

#  Başarılı İşlem (HTTP 200)
```bash
curl -X POST http://localhost:5000/pay -H "Content-Type: application/json" -d '{"amount": 100}'
```

#  Hatalı İşlem (HTTP 400 – log ve error trace yakalamak için)
```bash
curl -X POST http://localhost:5000/pay -H "Content-Type: application/json" -d '{"amount": -50}'
```


##  ArgoCD & CI/CD Workflow
ArgoCD ,gitlab tarafı ayrı bir expressjs uygulamasıyla entegre edilmiştir .


GitLab Runner, kaynak koddaki değişiklikleri algılayıp build işlemini tamamladıktan sonra deployment süreci **ArgoCD** tarafından yönetilir.


# ArgoCD arayüzüne erişim
```bash
KUBECONFIG=./k3s.yaml kubectl port-forward svc/argocd-server -n argocd 8080:443
```

- **ArgoCD UI:** https://localhost:8080  
  > Tarayıcıda **Gelişmiş → İlerle** diyerek SSL uyarısını geçebilirsiniz.
- **Kullanıcı:** `admin`


# Initial admin şifresini öğrenme
```bash
KUBECONFIG=./k3s.yaml  -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

###  Node.js Uygulamasına Erişim & CI/CD Güncelleme Akışı

GitLab reposundan çekilip **ArgoCD** tarafından deploy edilen Node.js uygulamasını görüntülemek ve kod değişikliklerinin Pod’lara yansımasını sağlamak için aşağıdaki adımları izleyin.

# Node.js uygulamasına erişim
```bash
KUBECONFIG=./k3s.yaml kubectl port-forward svc/my-node-app 3000:3000
```

- **Uygulama Adresi:** http://localhost:3000

Bu adres ile uygulamanın ana sayfasını görebilirsiniz, kodu değiştirip pushladığınızda kod gitlabda değişecek cı/cd pipelinesi sayesinde image oluşturulacak daha sonrasında ise. 

# Kod değişikliği sonrası (imaj tag'i değişmediyse) Pod'ları yeni imajı çekmeye zorla
```bash
KUBECONFIG=./k3s.yaml kubectl rollout restart deployment my-node-app -n default
```

### CI/CD Akışı Özeti

1. **Commit & Push**  
   Kaynak kodda gerekli değişiklikleri yapın ve GitLab reposuna commit ederek push edin.

2. **Build (GitLab Runner)**  
   GitLab Runner tarafından tetiklenen pipeline’ın build adımının tamamlanmasını bekleyin.

3. **Deploy (ArgoCD)**  
   ArgoCD, Git deposundaki değişiklikleri algılayarak deployment sürecini yönetir.  
   Eğer kullanılan imaj tag’i değişmiyorsa (ör. `latest`), Pod’ların güncellenmesi için manuel olarak rollout restart gerekebilir.






