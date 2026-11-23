#!/usr/bin/env bash
set -euo pipefail

main=src/main/java/com/acme/customers
test=src/test/java/com/acme/customers
mkdir -p "$main" "$test"

cat > pom.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
	<modelVersion>4.0.0</modelVersion>
	<parent>
		<groupId>org.springframework.boot</groupId>
		<artifactId>spring-boot-starter-parent</artifactId>
		<version>4.2.0</version>
		<relativePath/>
	</parent>
	<groupId>com.acme</groupId>
	<artifactId>customers</artifactId>
	<version>0.0.1-SNAPSHOT</version>
	<properties>
		<java.version>21</java.version>
	</properties>
	<dependencies>
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-starter-webmvc</artifactId>
		</dependency>
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-starter-webmvc-test</artifactId>
			<scope>test</scope>
		</dependency>
	</dependencies>
	<build>
		<plugins>
			<plugin>
				<groupId>org.springframework.boot</groupId>
				<artifactId>spring-boot-maven-plugin</artifactId>
			</plugin>
			<plugin>
				<groupId>org.apache.maven.plugins</groupId>
				<artifactId>maven-failsafe-plugin</artifactId>
				<executions>
					<execution>
						<goals>
							<goal>integration-test</goal>
							<goal>verify</goal>
						</goals>
					</execution>
				</executions>
			</plugin>
		</plugins>
	</build>
</project>
EOF

cat > "$main/CustomersApplication.java" <<'EOF'
package com.acme.customers;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CustomersApplication {

    public static void main(String[] args) {
        SpringApplication.run(CustomersApplication.class, args);
    }
}
EOF

cat > "$main/Customer.java" <<'EOF'
package com.acme.customers;

public record Customer(Long id, String name) {
}
EOF

cat > "$main/CustomerDirectory.java" <<'EOF'
package com.acme.customers;

import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Component;

@Component
public class CustomerDirectory {

    private final Map<Long, Customer> customers = Map.of(
        1L, new Customer(1L, "Ada Lovelace"),
        2L, new Customer(2L, "Grace Hopper"));

    public Optional<Customer> findById(Long id) {
        return Optional.ofNullable(customers.get(id));
    }
}
EOF

cat > "$main/CustomerController.java" <<'EOF'
package com.acme.customers;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/customers")
public class CustomerController {

    private final CustomerDirectory customerDirectory;

    public CustomerController(CustomerDirectory customerDirectory) {
        this.customerDirectory = customerDirectory;
    }

    @GetMapping("/{id}")
    public ResponseEntity<Customer> getCustomer(@PathVariable Long id) {
        return customerDirectory.findById(id)
            .map(ResponseEntity::ok)
            .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
EOF

cat > "$main/RequestIdFilter.java" <<'EOF'
package com.acme.customers;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class RequestIdFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        response.setHeader("X-Request-Id", UUID.randomUUID().toString());
        chain.doFilter(request, response);
    }
}
EOF

cat > "$test/CustomerControllerTest.java" <<'EOF'
package com.acme.customers;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@WebMvcTest(CustomerController.class)
class CustomerControllerTest {

    @Autowired
    private MockMvcTester mvc;

    @MockitoBean
    private CustomerDirectory customerDirectory;

    @Test
    void shouldReturnCustomerAsJson() {
        when(customerDirectory.findById(1L)).thenReturn(Optional.of(new Customer(1L, "Ada Lovelace")));

        assertThat(mvc.get().uri("/api/customers/1"))
            .hasStatusOk()
            .bodyJson().extractingPath("$.name").isEqualTo("Ada Lovelace");
    }

    @Test
    void shouldReturnNotFoundForUnknownCustomer() {
        when(customerDirectory.findById(42L)).thenReturn(Optional.empty());

        assertThat(mvc.get().uri("/api/customers/42")).hasStatus(HttpStatus.NOT_FOUND);
    }
}
EOF
