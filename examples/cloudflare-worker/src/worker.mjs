export default {
  fetch() {
    return new Response("Hello from the reusable CI/CD foundation.\n", {
      headers: { "content-type": "text/plain; charset=UTF-8" },
    });
  },
};