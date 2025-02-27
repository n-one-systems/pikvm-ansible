# ROLE: nsys.pikvm.init


## Sample Inventory
```yaml
all:
  children:
    pikvm:
      hosts:
        kvm-01.hq.my-company.com.:
          ansible_host: 198.51.100.11
        kvm-02.hq.my-company.com.:
          ansible_host: 198.51.100.12
        kvm-03.hq.my-company.com.:
          ansible_host: 198.51.100.13 
        kvm-04.hq.my-company.com.:
          ansible_host: 198.51.100.14 
```
