#!/usr/bin/env bash
set -euo pipefail

main=src/main/java/com/acme/docs/assignment
test=src/test/java/com/acme/docs/assignment
mkdir -p "$main" "$test" src/test/java/com/acme/docs/support

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
	<artifactId>docs</artifactId>
	<version>0.0.1-SNAPSHOT</version>
	<properties>
		<java.version>21</java.version>
	</properties>
	<dependencies>
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-starter-data-jpa</artifactId>
		</dependency>
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-starter-webmvc</artifactId>
		</dependency>
		<dependency>
			<groupId>org.postgresql</groupId>
			<artifactId>postgresql</artifactId>
			<scope>runtime</scope>
		</dependency>
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-starter-data-jpa-test</artifactId>
			<scope>test</scope>
		</dependency>
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-starter-webmvc-test</artifactId>
			<scope>test</scope>
		</dependency>
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-testcontainers</artifactId>
			<scope>test</scope>
		</dependency>
		<dependency>
			<groupId>org.testcontainers</groupId>
			<artifactId>testcontainers-postgresql</artifactId>
			<scope>test</scope>
		</dependency>
	</dependencies>
</project>
EOF

cat > "$main/Assignment.java" <<'EOF'
package com.acme.docs.assignment;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import java.time.LocalDate;

@Entity
public class Assignment {

    @Id
    @GeneratedValue
    private Long id;

    private Long documentId;

    private Long customerId;

    private LocalDate validTo;

    private boolean archived;

    protected Assignment() {
    }

    public Assignment(Long documentId, Long customerId, LocalDate validTo) {
        this.documentId = documentId;
        this.customerId = customerId;
        this.validTo = validTo;
    }

    public Long getCustomerId() {
        return customerId;
    }

    public LocalDate getValidTo() {
        return validTo;
    }

    public boolean isArchived() {
        return archived;
    }
}
EOF

cat > "$main/AssignmentRepository.java" <<'EOF'
package com.acme.docs.assignment;

import java.time.LocalDate;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

public interface AssignmentRepository extends JpaRepository<Assignment, Long> {

    List<Assignment> findByDocumentId(Long documentId);

    @Modifying
    @Query("update Assignment a set a.validTo = :validTo where a.documentId = :documentId and a.customerId in :customerIds")
    int updateValidTo(Long documentId, Collection<Long> customerIds, LocalDate validTo);

    @Modifying
    @Query("update Assignment a set a.archived = true where a.documentId = :documentId")
    int archiveByDocumentId(Long documentId);
}
EOF

cat > "$main/UpdateValidityRequest.java" <<'EOF'
package com.acme.docs.assignment;

import java.time.LocalDate;
import java.util.List;

public record UpdateValidityRequest(List<Long> customerIds, LocalDate validTo) {
}
EOF

cat > "$main/UpdateValidityUseCase.java" <<'EOF'
package com.acme.docs.assignment;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UpdateValidityUseCase {

    private final AssignmentRepository assignmentRepository;

    public UpdateValidityUseCase(AssignmentRepository assignmentRepository) {
        this.assignmentRepository = assignmentRepository;
    }

    @Transactional
    public void execute(Long documentId, UpdateValidityRequest request) {
        assignmentRepository.updateValidTo(documentId, request.customerIds(), request.validTo());
    }
}
EOF

cat > "$main/ArchiveDocumentUseCase.java" <<'EOF'
package com.acme.docs.assignment;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ArchiveDocumentUseCase {

    private final AssignmentRepository assignmentRepository;

    public ArchiveDocumentUseCase(AssignmentRepository assignmentRepository) {
        this.assignmentRepository = assignmentRepository;
    }

    @Transactional
    public ArchiveResult execute(Long documentId) {
        if (assignmentRepository.findByDocumentId(documentId).isEmpty()) {
            return ArchiveResult.nothingToArchive();
        }
        return ArchiveResult.archived(assignmentRepository.archiveByDocumentId(documentId));
    }
}
EOF

cat > "$main/ArchiveResult.java" <<'EOF'
package com.acme.docs.assignment;

public record ArchiveResult(int archivedAssignments) {

    public static ArchiveResult nothingToArchive() {
        return new ArchiveResult(0);
    }

    public static ArchiveResult archived(int count) {
        return new ArchiveResult(count);
    }
}
EOF

cat > "$test/ArchiveDocumentUseCaseTest.java" <<'EOF'
package com.acme.docs.assignment;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ArchiveDocumentUseCaseTest {

    @Mock
    private AssignmentRepository assignmentRepository;

    @InjectMocks
    private ArchiveDocumentUseCase useCase;

    @Test
    void shouldArchiveAllAssignmentsOfDocument() {
        when(assignmentRepository.findByDocumentId(7L))
            .thenReturn(List.of(new Assignment(7L, 1L, LocalDate.of(2027, 1, 31))));
        when(assignmentRepository.archiveByDocumentId(7L)).thenReturn(1);

        var result = useCase.execute(7L);

        assertThat(result.archivedAssignments()).isEqualTo(1);
    }

    @Test
    void shouldNotArchiveDocumentWithoutAssignments() {
        when(assignmentRepository.findByDocumentId(7L)).thenReturn(List.of());

        var result = useCase.execute(7L);

        assertThat(result.archivedAssignments()).isZero();
        verify(assignmentRepository, never()).archiveByDocumentId(7L);
    }
}
EOF

cat > "$test/AssignmentRepositoryTest.java" <<'EOF'
package com.acme.docs.assignment;

import static org.assertj.core.api.Assertions.assertThat;

import com.acme.docs.support.SharedPostgres;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest;
import org.springframework.boot.jdbc.test.autoconfigure.AutoConfigureTestDatabase;
import org.springframework.boot.jpa.test.autoconfigure.TestEntityManager;
import org.springframework.boot.testcontainers.context.ImportTestcontainers;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@ImportTestcontainers(SharedPostgres.class)
class AssignmentRepositoryTest {

    @Autowired
    private AssignmentRepository repository;

    @Autowired
    private TestEntityManager entityManager;

    @Test
    void shouldUpdateValidToOnlyForSelectedCustomers() {
        entityManager.persist(new Assignment(7L, 1L, LocalDate.of(2026, 12, 31)));
        entityManager.persist(new Assignment(7L, 2L, LocalDate.of(2026, 12, 31)));
        entityManager.flush();

        var updated = repository.updateValidTo(7L, List.of(1L), LocalDate.of(2027, 6, 30));
        entityManager.clear();

        assertThat(updated).isEqualTo(1);
        assertThat(repository.findByDocumentId(7L))
            .filteredOn(assignment -> assignment.getCustomerId().equals(2L))
            .extracting(Assignment::getValidTo)
            .containsExactly(LocalDate.of(2026, 12, 31));
    }
}
EOF

cat > src/test/java/com/acme/docs/support/SharedPostgres.java <<'EOF'
package com.acme.docs.support;

import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.testcontainers.postgresql.PostgreSQLContainer;

public final class SharedPostgres {

    @ServiceConnection
    static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer("postgres:17.2");
}
EOF

cat > src/test/java/com/acme/docs/support/AbstractIntegrationTest.java <<'EOF'
package com.acme.docs.support;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.context.ImportTestcontainers;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("integration-test")
@ImportTestcontainers(SharedPostgres.class)
public abstract class AbstractIntegrationTest {
}
EOF
