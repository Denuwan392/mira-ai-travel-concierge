import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PasswordField } from "@/components/auth/PasswordField";
import { AuthField } from "@/components/auth/AuthField";
import { AuthSplitLayout } from "@/components/auth/AuthSplitLayout";
import LoginPage from "@/routes/login";
import RegisterPage from "@/routes/register";
import * as liveService from "@/lib/live/service";

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => () => ({ component: vi.fn() }),
  useRouter: () => ({ navigate: vi.fn() }),
  Link: ({ to, children, className, ...props }: any) => (
    <a href={to} className={className} {...props}>
      {children}
    </a>
  ),
}));

describe("Authentication UI Components", () => {
  describe("PasswordField", () => {
    it("renders as type='password' by default with accessible toggle", () => {
      render(
        <PasswordField
          id="test-pwd"
          label="Password"
          value="Secret123!"
          onChange={() => {}}
        />
      );

      const input = screen.getByLabelText("Password");
      expect(input).toBeDefined();
      expect(input.getAttribute("type")).toBe("password");

      const toggleBtn = screen.getByLabelText("Show password");
      expect(toggleBtn).toBeDefined();
    });

    it("toggles password visibility between password and text", () => {
      render(
        <PasswordField
          id="test-pwd"
          label="Password"
          value="Secret123!"
          onChange={() => {}}
        />
      );

      const input = screen.getByLabelText("Password");
      const toggleBtn = screen.getByLabelText("Show password");

      // Click to show password
      fireEvent.click(toggleBtn);
      expect(input.getAttribute("type")).toBe("text");
      expect(screen.getByLabelText("Hide password")).toBeDefined();

      // Click again to hide password
      fireEvent.click(screen.getByLabelText("Hide password"));
      expect(input.getAttribute("type")).toBe("password");
      expect(screen.getByLabelText("Show password")).toBeDefined();
    });

    it("renders hint and error messages with correct ARIA associations", () => {
      render(
        <PasswordField
          id="test-pwd"
          label="Password"
          value=""
          hint="Minimum 8 characters"
          error="Password is required"
          onChange={() => {}}
        />
      );

      expect(screen.getByText("Minimum 8 characters")).toBeDefined();
      const errorMsg = screen.getByText("Password is required");
      expect(errorMsg).toBeDefined();
      expect(errorMsg.getAttribute("id")).toBe("test-pwd-error");

      const input = screen.getByLabelText("Password");
      expect(input.getAttribute("aria-invalid")).toBe("true");
      expect(input.getAttribute("aria-describedby")).toBe("test-pwd-error");
    });
  });

  describe("AuthField", () => {
    it("renders text input with associated label and required indicator", () => {
      render(
        <AuthField
          id="test-email"
          label="Email address"
          type="email"
          required
          value="test@example.com"
          placeholder="Enter email"
          onChange={() => {}}
        />
      );

      const input = screen.getByLabelText(/Email address/);
      expect(input).toBeDefined();
      expect(input.getAttribute("type")).toBe("email");
      expect(input.getAttribute("required")).toBe("");
      expect(input.getAttribute("placeholder")).toBe("Enter email");
    });

    it("displays error with accessible ARIA linking", () => {
      render(
        <AuthField
          id="test-field"
          label="Full name"
          value=""
          error="Full name is required"
          onChange={() => {}}
        />
      );

      const input = screen.getByLabelText("Full name");
      expect(input.getAttribute("aria-invalid")).toBe("true");
      expect(input.getAttribute("aria-describedby")).toBe("test-field-error");
      expect(screen.getByText("Full name is required")).toBeDefined();
    });
  });

  describe("AuthSplitLayout", () => {
    it("renders editorial storytelling headline and child form container", () => {
      render(
        <AuthSplitLayout
          eyebrow="CEYLON COMPASS HOLIDAYS"
          headline="Your next story begins in Sri Lanka."
          subtext="Discover remarkable places, thoughtful journeys, and experiences designed around you."
        >
          <div data-testid="test-form">Form Content</div>
        </AuthSplitLayout>
      );

      expect(screen.getByTestId("test-form")).toBeDefined();
      const headlines = screen.getAllByText("Your next story begins in Sri Lanka.");
      expect(headlines.length).toBeGreaterThan(0);
      expect(screen.getByText(/Discover remarkable places/)).toBeDefined();
    });
  });

  describe("LoginPage Integration", () => {
    beforeEach(() => {
      vi.restoreAllMocks();
    });

    it("renders split-screen storytelling, inputs, and submission button", () => {
      render(<LoginPage />);

      expect(screen.getByRole("heading", { name: "Welcome back" })).toBeDefined();
      expect(screen.getByText("Sign in to continue your Sri Lanka journey.")).toBeDefined();
      expect(screen.getByLabelText(/Email address/)).toBeDefined();
      expect(screen.getByLabelText("Password")).toBeDefined();
      expect(screen.getByLabelText("Remember this browser for 30 days")).toBeDefined();
      expect(screen.getByRole("button", { name: "Sign in" })).toBeDefined();
      expect(screen.getByText("Create an account")).toBeDefined();
    });

    it("submits form and calls /auth/login with credentials", async () => {
      const apiSpy = vi.spyOn(liveService, "api").mockResolvedValueOnce({
        id: "usr-1",
        role: "traveller",
        full_name: "Kamal Perera",
      });

      render(<LoginPage />);

      fireEvent.change(screen.getByLabelText(/Email address/), {
        target: { value: "traveller@example.com" },
      });
      fireEvent.change(screen.getByLabelText("Password"), {
        target: { value: "Password123!" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

      await waitFor(() => {
        expect(apiSpy).toHaveBeenCalledWith("/auth/login", expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            email: "traveller@example.com",
            password: "Password123!",
            remember: true,
          }),
        }));
      });

      expect(await screen.findByText(/Signed in successfully/)).toBeDefined();
    });

    it("displays error message when login fails", async () => {
      vi.spyOn(liveService, "api").mockRejectedValueOnce(
        new Error("Invalid email or password.")
      );

      render(<LoginPage />);

      fireEvent.change(screen.getByLabelText(/Email address/), {
        target: { value: "wrong@example.com" },
      });
      fireEvent.change(screen.getByLabelText("Password"), {
        target: { value: "WrongPassword" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

      const alert = await screen.findByRole("alert");
      expect(alert.textContent).toContain("Invalid email or password.");
    });
  });

  describe("RegisterPage Integration", () => {
    beforeEach(() => {
      vi.restoreAllMocks();
    });

    it("renders split-screen storytelling, registration inputs, and CTA", () => {
      render(<RegisterPage />);

      expect(screen.getByRole("heading", { name: "Create your account" })).toBeDefined();
      expect(screen.getByText("Keep your journeys, saved quotes, and travel preferences together.")).toBeDefined();
      expect(screen.getByLabelText(/Full name/)).toBeDefined();
      expect(screen.getByLabelText(/Email address/)).toBeDefined();
      expect(screen.getByLabelText("Password")).toBeDefined();
      expect(screen.getByLabelText(/Contact phone/)).toBeDefined();
      expect(screen.getByRole("button", { name: "Create account" })).toBeDefined();
      expect(screen.getByText("Sign in")).toBeDefined();
    });

    it("blocks submission if password is under 8 characters", async () => {
      const apiSpy = vi.spyOn(liveService, "api");
      render(<RegisterPage />);

      fireEvent.change(screen.getByLabelText(/Full name/), {
        target: { value: "Saman Perera" },
      });
      fireEvent.change(screen.getByLabelText(/Email address/), {
        target: { value: "saman@example.com" },
      });
      fireEvent.change(screen.getByLabelText("Password"), {
        target: { value: "short" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Create account" }));

      const alert = await screen.findByRole("alert");
      expect(alert.textContent).toContain("Password must be at least 8 characters.");
      expect(apiSpy).not.toHaveBeenCalled();
    });

    it("submits registration with valid fields", async () => {
      const apiSpy = vi.spyOn(liveService, "api").mockResolvedValueOnce({
        id: "usr-2",
        role: "traveller",
        full_name: "Saman Perera",
      });

      render(<RegisterPage />);

      fireEvent.change(screen.getByLabelText(/Full name/), {
        target: { value: "Saman Perera" },
      });
      fireEvent.change(screen.getByLabelText(/Email address/), {
        target: { value: "saman@example.com" },
      });
      fireEvent.change(screen.getByLabelText("Password"), {
        target: { value: "ValidPassword123!" },
      });
      fireEvent.change(screen.getByLabelText(/Contact phone/), {
        target: { value: "+94 77 123 4567" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Create account" }));

      await waitFor(() => {
        expect(apiSpy).toHaveBeenCalledWith("/auth/register", expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            full_name: "Saman Perera",
            email: "saman@example.com",
            password: "ValidPassword123!",
            phone: "+94 77 123 4567",
            preferences: {},
          }),
        }));
      });

      expect(await screen.findByText(/Account created successfully/)).toBeDefined();
    });
  });
});
