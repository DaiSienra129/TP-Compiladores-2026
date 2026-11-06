#include <stdio.h>
#include "identificador.h"

int main() {
    const char *casos[] = {
        "contador2",  // Debería ser válido
        "_var_1",     // Debería ser válido
        "2contador",  // Debería ser inválido
        "a-b",        // Debería ser inválido
        NULL
    };

    for (int i = 0; casos[i] != NULL; i++) {
        if (validar_id(casos[i])) {
            printf("Aceptado: %s\n", casos[i]);
        } else {
            printf("Rechazado: %s\n", casos[i]);
        }
    }
    return 0;
}