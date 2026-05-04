import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import HotelsListPage from "./pages/hotels/HotelsListPage";
import HotelDetailPage from "./pages/hotels/HotelDetailPage";
import MyBookingsPage from "./pages/hotels/MyBookingsPage";
import AttractionsListPage from "./pages/attractions/AttractionsListPage";
import AttractionDetailPage from "./pages/attractions/AttractionDetailPage";
import FoodListPage from "./pages/food/FoodListPage";
import FoodDetailPage from "./pages/food/FoodDetailPage";
import TransportPage from "./pages/transport/TransportPage";
import RentalsListPage from "./pages/rentals/RentalsListPage";
import RentalDetailPage from "./pages/rentals/RentalDetailPage";
import ChatbotPage from "./pages/chatbot/ChatbotPage";


export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/"              element={<Home />} />
        <Route path="/login"         element={<Login />} />
        <Route path="/register"      element={<Register />} />
        <Route path="/profile"       element={<Profile />} />
        <Route path="/hotels"        element={<HotelsListPage />} />
        <Route path="/hotels/:id"    element={<HotelDetailPage />} />
        <Route path="/my-bookings"   element={<MyBookingsPage />} />
        <Route path="/attractions"     element={<AttractionsListPage />} />
        <Route path="/attractions/:id" element={<AttractionDetailPage />} />
        <Route path="/food"     element={<FoodListPage />} />
        <Route path="/food/:id" element={<FoodDetailPage />} />
        <Route path="/transport" element={<TransportPage />} />
        <Route path="/rentals"     element={<RentalsListPage />} />
        <Route path="/rentals/:id" element={<RentalDetailPage />} />
        <Route path="/chatbot" element={<ChatbotPage />} />
      </Routes>
      <Footer />
    </BrowserRouter>
  );
}
