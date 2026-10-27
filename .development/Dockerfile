FROM frappe/erpnext@sha256:4160d3c77aafb41c7770aad3daa67254a13f8750765ee83d632434ed564a4834
USER root
COPY --chown=frappe:frappe repos/erpnext/ /home/frappe/frappe-bench/apps/erpnext/
LABEL org.opencontainers.image.revision="4e0dce9ea8d351cd7023ad5ed66faf3cdec0680e"
USER frappe
