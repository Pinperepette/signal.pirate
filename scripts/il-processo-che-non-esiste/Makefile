obj-m += rootkit.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) clean

load:
	sudo insmod rootkit.ko

unload:
	sudo rmmod rootkit

status:
	@echo "=== dmesg (ultimi 20) ==="
	@sudo dmesg | tail -20
	@echo ""
	@echo "=== lsmod ==="
	@lsmod | grep rootkit || echo "(non trovato)"
	@echo ""
	@echo "=== /proc/sp_rootkit ==="
	@cat /proc/sp_rootkit 2>/dev/null || echo "(non presente)"
