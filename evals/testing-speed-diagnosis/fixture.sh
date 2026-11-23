#!/usr/bin/env bash
set -euo pipefail

reports=target/surefire-reports
tests=src/test/java/com/acme/shop
mkdir -p "$reports" "$tests/export" "$tests/order" "$tests/pricing"

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
	<artifactId>shop</artifactId>
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
</project>
EOF

report() {
    local class_name=$1 total=$2 count=$3 each=$4
    {
        echo '<?xml version="1.0" encoding="UTF-8"?>'
        echo "<testsuite name=\"$class_name\" time=\"$total\" tests=\"$count\" errors=\"0\" skipped=\"0\" failures=\"0\">"
        for index in $(seq 1 "$count"); do
            echo "  <testcase name=\"shouldHandleCase$index\" classname=\"$class_name\" time=\"$each\"/>"
        done
        echo '</testsuite>'
    } > "$reports/TEST-$class_name.xml"
}

report com.acme.shop.export.OrderExportServiceTest 182.412 12 15.201
report com.acme.shop.shipping.ShippingApiTest 11.204 4 2.801
report com.acme.shop.invoice.InvoiceApiTest 10.633 5 2.126
report com.acme.shop.payment.PaymentApiTest 10.118 3 3.372
report com.acme.shop.customer.CustomerApiTest 9.847 6 1.641
report com.acme.shop.catalog.CatalogApiTest 9.402 4 2.350
report com.acme.shop.order.OrderControllerTest 2.096 7 0.299
report com.acme.shop.order.OrderServiceTest 0.412 9 0.045
report com.acme.shop.pricing.PriceCalculatorTest 0.287 14 0.020

cat > "$tests/export/OrderExportServiceTest.java" <<'EOF'
package com.acme.shop.export;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class OrderExportServiceTest {

    private final InMemoryExportStore store = new InMemoryExportStore();

    private final OrderExportService service = new OrderExportService(store);

    @ParameterizedTest
    @ValueSource(strings = {"CSV", "XML", "JSON", "PDF", "XLSX", "EDI", "CSV_GZ", "XML_GZ", "JSON_GZ", "PDF_A", "ODS", "TXT"})
    void shouldWriteExportInRequestedFormat(String format) throws InterruptedException {
        service.exportAsync(4711L, format);

        Thread.sleep(15_000);

        assertThat(store.find(4711L, format)).isPresent();
    }
}
EOF

api_test() {
    local package=$1 class_name=$2 profile=$3 mock_one=$4 field_one=$5 mock_two=$6 field_two=$7
    mkdir -p "$tests/$package"
    cat > "$tests/$package/$class_name.java" <<EOF
package com.acme.shop.$package;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("$profile")
class $class_name {

    @Autowired
    private MockMvcTester mvc;

    @MockitoBean
    private $mock_one $field_one;

    @MockitoBean
    private $mock_two $field_two;

    @Test
    void shouldAnswerHealthProbe() {
        assertThat(mvc.get().uri("/api/$package/health")).hasStatusOk();
    }
}
EOF
}

api_test shipping ShippingApiTest test CarrierClient carrierClient LabelPrinter labelPrinter
api_test invoice InvoiceApiTest test-invoice TaxClient taxClient PdfRenderer pdfRenderer
api_test payment PaymentApiTest test PaymentGateway paymentGateway FraudCheck fraudCheck
api_test customer CustomerApiTest test-customer AddressValidator addressValidator MailSender mailSender
api_test catalog CatalogApiTest test SearchIndex searchIndex ImageStore imageStore

cat > "$tests/order/OrderControllerTest.java" <<'EOF'
package com.acme.shop.order;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired
    private MockMvcTester mvc;

    @MockitoBean
    private OrderService orderService;

    @Test
    void shouldReturnNotFoundForUnknownOrder() {
        assertThat(mvc.get().uri("/api/orders/42")).hasStatus(HttpStatus.NOT_FOUND);
    }
}
EOF

cat > "$tests/order/OrderServiceTest.java" <<'EOF'
package com.acme.shop.order;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class OrderServiceTest {

    @Test
    void shouldRejectEmptyOrder() {
        assertThat(new OrderService().accepts(Order.empty())).isFalse();
    }
}
EOF

cat > "$tests/pricing/PriceCalculatorTest.java" <<'EOF'
package com.acme.shop.pricing;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class PriceCalculatorTest {

    @Test
    void shouldApplyNoDiscountBelowThreshold() {
        assertThat(new PriceCalculator().discountFor(999)).isZero();
    }
}
EOF
